"""编排层：Planner → Executor 的状态机。

预算闸门（MAX_STEPS / 超时）在这里生效；写操作在这里被拦成"待确认"，
确认后由前端带 confirmed=true 再调一次，保证 AI 不会自己动手改数据。
"""

from __future__ import annotations

import time

from app import config
from app.context import resolve
from app.guard import PermissionDenied, audit
from app.guard import check as guard_check
from app.policies import check_write
from app.planner import LLMPlanner
from app.store import save_trace
from app.tools import get_tool, validate_args
from app.trace import Trace


def _render(trace: Trace) -> str:
    """规则版答案生成（不依赖 LLM，离线可测）。"""
    parts: list[str] = []
    for step in trace.steps:
        if step.status != "ok":
            continue
        data = step.result or {}
        if step.tool == "query_my_leave_balance":
            items = data.get("balances") or []
            detail = "、".join(f"{i['leave_type']} 剩余 {i['remaining_days']} 天（共 {i['total_days']} 天）" for i in items)
            parts.append(f"你的假期情况：{detail}。")
        elif step.tool == "query_my_attendance":
            parts.append(f"{data.get('month')} 考勤：共 {data.get('records')} 条记录，迟到 {data.get('late')} 次、缺勤 {data.get('absent')} 次。")
        elif step.tool == "query_my_salary":
            if data.get("found"):
                parts.append(f"{data.get('month')} 薪资已发放，金额区间 {data.get('range')} 元（明细见系统）。")
            else:
                parts.append(f"{data.get('month')} 暂无薪资记录。")
        elif step.tool == "submit_leave":
            if data.get("idempotent"):
                parts.append(f"已存在相同的{data.get('leave_type')}申请（单号 {data.get('leave_id')}，状态 {data.get('status')}），本次未重复提交。")
            else:
                parts.append(f"已提交{data.get('leave_type')}申请：{data.get('days')} 天，状态 {data.get('status')}，单号 {data.get('leave_id')}。")
        elif step.tool == "list_pending_approvals":
            items = data.get("items") or []
            if not items:
                parts.append("当前没有待审批的请假申请。")
            else:
                brief = "；".join(f"#{i['id']} {i['user']} {i['type']} {i['start']}~{i['end']}" for i in items[:5])
                parts.append(f"待审批 {data.get('count')} 条：{brief}。")
        elif step.tool == "approve_leave":
            if data.get("idempotent"):
                parts.append(f"请假单 #{data.get('leave_id')} 已是 {data.get('status')} 状态，本次未重复审批。")
            elif data.get("not_found"):
                parts.append(f"未找到请假单 #{data.get('leave_id')}，请确认单号。")
            elif data.get("approved"):
                parts.append(f"已通过请假单 #{data.get('leave_id')}。")
            else:
                parts.append(f"请假单 #{data.get('leave_id')} 未处理，请查看当前状态。")
        elif step.tool == "search_policy":
            if data.get("available"):
                src = "、".join(f"[{s['index']}] {s['title']}" for s in (data.get("sources") or []))
                parts.append(f"{data.get('answer')}" + (f"（来源：{src}）" if src else ""))
            else:
                parts.append("制度库当前不可用，建议稍后重试或联系 HR。")
    return " ".join(parts) or "没有可用的结果。"


class Orchestrator:
    def __init__(self, ctx: dict, planner=None):
        self.ctx = ctx
        self.planner = planner or LLMPlanner()

    def run(self, query: str, confirmed: bool = False, session_id: str | None = None) -> Trace:
        trace = Trace(query=query, role=self.ctx["role"], user=self.ctx.get("name", ""))
        deadline = time.time() + config.TIMEOUT_SECONDS

        # 相对时间（这个月/上个月）先做确定性替换，再交给 Planner
        resolved, _ = resolve(query)
        plan = self.planner.plan(resolved, self.ctx["role"])
        trace.verdict = {"intent": plan.intent, "note": plan.note, "planned": len(plan.calls),
                         "planner": plan.planner, "tokens": plan.tokens, "fallback": plan.fallback,
                         "session_id": session_id,
                         "resolved_query": resolved if resolved != query else None}

        if not plan.calls:
            trace.answer = ("没找到能处理这个请求的工具。" + (f"（{plan.note}）" if plan.note else "")
                            + "可以试试：查年假余额、查本月考勤、查待审批、问制度。")
            trace.save()
            return trace

        calls = plan.calls
        if len(calls) > config.MAX_STEPS:
            calls = calls[: config.MAX_STEPS]
            trace.truncated = True

        for call in calls:
            if time.time() > deadline:
                trace.add(call.tool, call.args, "timeout", 0, error="超出总时限")
                break
            spec = get_tool(call.tool)
            try:
                validate_args(spec, call.args)
            except ValueError as exc:
                trace.add(call.tool, call.args, "invalid_args", 0, error=str(exc))
                continue
            # 权限判断不能交给模型：执行前用角色硬校验，越权直接抛异常
            try:
                guard_check(spec, self.ctx["role"], call.args, {"name": self.ctx.get("name")})
            except PermissionDenied as exc:
                trace.add(call.tool, call.args, "denied", 0, error=str(exc))
                trace.verdict.update({"denied": True, "deny_reason": str(exc), "attempted_tool": call.tool})
                trace.answer = str(exc) + "。已拒绝执行并记录审计。"
                trace.save()
                return trace
            # 写操作前置校验：余额不足直接拦，不进入人工确认
            if spec.write:
                observations = [s.result for s in trace.steps if s.status == "ok"]
                allowed, reason, extra = check_write(
                    self.ctx, call, [{"result": r} for r in observations])
                if extra:
                    trace.add(extra["tool"], {}, "ok", 0, result=extra["result"])
                if not allowed:
                    trace.verdict.update({"blocked": True, "blocked_reason": reason})
                    trace.answer = reason
                    trace.save()
                    return trace

            if spec.requires_confirm and not confirmed:
                trace.verdict["pending_action"] = {"tool": call.tool, "args": call.args}
                trace.answer = f"准备执行写操作 {call.tool}，请确认后我再提交。"
                trace.save()
                return trace
            started = time.time()
            try:
                result = spec.handler(self.ctx, **call.args)
                trace.add(call.tool, call.args, "ok", int((time.time() - started) * 1000), result=result)
            except PermissionDenied:
                raise
            except Exception as exc:
                trace.add(call.tool, call.args, "error", int((time.time() - started) * 1000), error=str(exc))

        trace.answer = _render(trace)
        if any(s.status == "ok" for s in trace.steps):
            audit({"event": "task_done", "role": trace.role, "user": trace.user,
                   "query": query, "steps": [s.tool for s in trace.steps]})
        trace.save()
        save_trace(trace)
        return trace
