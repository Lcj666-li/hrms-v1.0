"""Planner：把自然语言拆成工具调用序列。

两种实现：
- RulePlanner：关键词 + 正则，确定性、零成本、离线可跑（基线）；
- LLMPlanner：function calling，把工具 schema 交给模型自选（expose_all=True 时故意暴露
  全部工具，用来验证"模型选错工具时 guard 能否兜住"）。

LLM 调用失败（网络/鉴权/格式）时自动降级到 RulePlanner，并计数，方便评测里报"降级率"。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from app import config
from app.llm_client import LLMError, chat
from app.tools.base import ToolCall, get_tool, to_openai_tool

DATE_RE = re.compile(r"(20\d{2}-\d{1,2}-\d{1,2})")
MONTH_RE = re.compile(r"(20\d{2}-\d{1,2})")

SYSTEM_PROMPT = """你是 HR 事务 Agent 的 Planner。根据问题从工具中选出调用序列（最多 3 步）。
规则：只用给定工具；参数符合 schema；含日期区间且要求提交/申请/提上去 → submit_leave（写操作照常调用，系统会要求人工确认）；无关问题返回空数组。
输出 JSON：{"steps":[{"tool":"名称","args":{},"why":"原因"}]}
"""


@dataclass
class Plan:
    calls: list[ToolCall] = field(default_factory=list)
    intent: str = "unknown"
    note: str = ""
    planner: str = "rule"
    tokens: int = 0
    fallback: bool = False


def _this_month() -> str:
    return date.today().strftime("%Y-%m")


def _next_week_range() -> tuple[str, str]:
    today = date.today()
    monday = today + timedelta(days=(7 - today.weekday()))
    return str(monday), str(monday + timedelta(days=4))


class RulePlanner:
    """关键词 + 正则的确定性 Planner（基线）。"""

    name = "rule"

    def plan(self, query: str, role: str) -> Plan:
        text = (query or "").strip()
        if not text:
            return Plan(note="空问题", planner=self.name)

        if any(k in text for k in ("制度", "规定", "政策", "能不能请", "怎么算", "报销")):
            return Plan(intent="policy", planner=self.name,
                        calls=[ToolCall(tool="search_policy", args={"question": text}, why="制度类问题，查知识库")])

        if any(k in text for k in ("通过", "批准", "同意")):
            ids = re.findall(r"\b(\d{1,6})\b", text)
            if ids:
                return Plan(intent="approve", planner=self.name,
                            calls=[ToolCall(tool="approve_leave",
                                            args={"leave_id": int(ids[0]), "comment": "按制度审批通过"},
                                            why="审批写操作，需确认")])

        if any(k in text for k in ("待审批", "审批列表", "等我审批")):
            return Plan(intent="pending", planner=self.name,
                        calls=[ToolCall(tool="list_pending_approvals", args={}, why="主管查看待审批")])

        if any(k in text for k in ("请假", "提交申请", "帮我请")):
            dates = DATE_RE.findall(text)
            start, end = (dates[0], dates[1]) if len(dates) >= 2 else _next_week_range()
            leave_type = "年假"
            for name in ("年假", "病假", "事假", "调休"):
                if name in text:
                    leave_type = name
                    break
            reason = text.split("因为", 1)[1][:80] if "因为" in text else "Agent 代为提交"
            return Plan(intent="submit_leave", planner=self.name,
                        calls=[ToolCall(tool="submit_leave",
                                        args={"leave_type": leave_type, "start_date": start, "end_date": end,
                                              "reason": reason}, why="提交请假：写操作，需确认")])

        if any(k in text for k in ("年假", "余额", "还剩", "剩余", "假期")):
            return Plan(intent="leave_balance", planner=self.name,
                        calls=[ToolCall(tool="query_my_leave_balance", args={}, why="查假期余额")])

        if any(k in text for k in ("考勤", "打卡", "迟到", "缺勤")):
            month = (MONTH_RE.findall(text) or [_this_month()])[0]
            return Plan(intent="attendance", planner=self.name,
                        calls=[ToolCall(tool="query_my_attendance", args={"month": month}, why="查考勤")])

        if any(k in text for k in ("工资", "薪资", "薪水", "发了多少")):
            month = (MONTH_RE.findall(text) or [_this_month()])[0]
            return Plan(intent="salary", planner=self.name,
                        calls=[ToolCall(tool="query_my_salary", args={"month": month}, why="查薪资")])

        return Plan(note="没有匹配到可用工具", planner=self.name)


class LLMPlanner:
    """function calling 版 Planner。"""

    name = "llm"

    def __init__(self, expose_all: bool = False) -> None:
        # expose_all=True：故意把主管工具也给员工，用来验证 guard 的必要性
        self.expose_all = expose_all
        if expose_all:
            self.name = "llm_all"

    def _tools(self, role: str) -> list[dict]:
        from app.tools.base import REGISTRY
        specs = list(REGISTRY.values()) if self.expose_all else [s for s in REGISTRY.values() if role in s.roles]
        return [to_openai_tool(spec) for spec in specs]

    def plan(self, query: str, role: str) -> Plan:
        if not config.LLM_API_KEY:
            plan = RulePlanner().plan(query, role)
            plan.planner, plan.fallback = "rule(fallback)", True
            return plan

        role_hint = "\n角色：" + role + ("（主管无个人请假/年假/考勤接口，此类诉求返回空 steps）" if role == "manager" else "。")
        today_hint = "\n今天是 " + date.today().isoformat() + "。"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + role_hint + today_hint},
            {"role": "user", "content": query},
        ]
        try:
            message, usage = chat(messages, tools=self._tools(role), max_tokens=400)
        except LLMError:
            plan = RulePlanner().plan(query, role)
            plan.planner, plan.fallback = "rule(fallback)", True
            return plan

        calls = self._sanitize(self._parse(message))
        tokens = int((usage or {}).get("total_tokens") or 0)
        if not calls:
            note = (message.get("content") or "").strip()[:200]
            return Plan(note=note or "模型判断无需调用工具", planner=self.name, tokens=tokens)
        return Plan(intent="llm", calls=calls, planner=self.name, tokens=tokens)

    @staticmethod
    def _sanitize(calls: list[ToolCall]) -> list[ToolCall]:
        """裁掉模型多给/写错的参数名（模型常加 limit、status 之类），保留合法参数。"""
        from app.tools.base import REGISTRY

        cleaned = []
        for call in calls:
            spec = REGISTRY.get(call.tool)
            if spec is None:
                continue
            args = {k: v for k, v in call.args.items() if k in spec.params}
            cleaned.append(ToolCall(tool=call.tool, args=args, why=call.why))
        return cleaned

    @staticmethod
    def _parse(message: dict) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            fn = item.get("function") or {}
            name = fn.get("name")
            if not name:
                continue
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(tool=name, args=args, why="llm"))
        if calls:
            return calls

        # 兼容：模型把计划写在 content 里的 JSON
        content = (message.get("content") or "").strip()
        if not content:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                return []
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        for step in data.get("steps") or []:
            name = step.get("tool")
            if name and name in {s for s in __import__("app.tools.base", fromlist=["REGISTRY"]).REGISTRY}:
                calls.append(ToolCall(tool=name, args=step.get("args") or {}, why=step.get("why", "llm")))
        return calls


HIGH_CONFIDENCE_INTENTS = {
    "policy", "approve", "pending", "submit_leave",
    "leave_balance", "attendance", "salary",
}


class HybridPlanner:
    """路由型 Planner：规则命中高置信意图就走规则（0 token），否则交 LLM。"""

    name = "hybrid"

    def __init__(self) -> None:
        self.rule = RulePlanner()
        self.llm = LLMPlanner(expose_all=False)

    def plan(self, query: str, role: str) -> Plan:
        rule_plan = self.rule.plan(query, role)
        if rule_plan.calls and self._confident(rule_plan):
            rule_plan.planner = "hybrid(rule)"
            return rule_plan
        llm_plan = self.llm.plan(query, role)
        if llm_plan.planner.startswith("llm"):
            llm_plan.planner = "hybrid(llm)"
        return llm_plan

    @staticmethod
    def _confident(plan: Plan) -> bool:
        from app.tools.base import get_tool, validate_args
        if plan.intent not in HIGH_CONFIDENCE_INTENTS:
            return False
        for call in plan.calls:
            try:
                validate_args(get_tool(call.tool), call.args)
            except Exception:
                return False
        return True


def build_planner(kind: str):
    if kind == "rule":
        return RulePlanner()
    if kind == "llm":
        return LLMPlanner(expose_all=False)
    if kind == "llm_all":
        return LLMPlanner(expose_all=True)
    if kind == "hybrid":
        return HybridPlanner()
    raise ValueError(f"未知 planner：{kind}")
