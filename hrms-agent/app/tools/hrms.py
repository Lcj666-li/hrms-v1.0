"""HRMS 业务工具：全部走 HRMS 的 REST 接口（不直连数据库）。

这样做的原因：
- 权限校验、数据校验、审计仍在业务系统里，Agent 不绕过原有边界；
- 工具只负责"把用户的一句话翻译成一次 API 调用"，好测、好替换。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from app.tools.base import tool

LEAVE_TYPE_ALIAS = {
    "年假": "annual",
    "annual": "annual",
    "病假": "sick",
    "sick": "sick",
    "事假": "personal",
    "personal": "personal",
    "调休": "compensatory",
    "compensatory": "compensatory",
}


def _client(ctx: dict, timeout: float = 15.0) -> httpx.Client:
    return httpx.Client(
        base_url=ctx["base_url"],
        headers={"Authorization": f"Bearer {ctx['token']}"},
        timeout=timeout,
    )


def _days(start: str, end: str) -> int:
    d1 = datetime.strptime(start, "%Y-%m-%d").date()
    d2 = datetime.strptime(end, "%Y-%m-%d").date()
    if d2 < d1:
        raise ValueError("结束日期不能早于开始日期")
    return (d2 - d1).days + 1


def _resolve_leave_type(client: httpx.Client, name: str) -> dict:
    resp = client.get("/api/leave-types")
    resp.raise_for_status()
    items = resp.json() or []
    code = LEAVE_TYPE_ALIAS.get(name.strip(), name.strip())
    for item in items:
        if item.get("code") == code or item.get("name") == name:
            return item
    raise ValueError(f"未找到请假类型：{name}（可选：年假/病假/事假/调休）")


@tool(
    name="query_my_leave_balance",
    description="查询当前员工各类假期的总额度与剩余天数（只返回本人）",
    params={},
    roles=("employee",),
)
def query_my_leave_balance(ctx: dict) -> dict[str, Any]:
    with _client(ctx) as client:
        types = client.get("/api/leave-types").json() or []
        leaves = client.get("/api/leave/my").json() or []
    used: dict[int, float] = {}
    for item in leaves:
        if item.get("status") not in ("approved", "pending"):
            continue
        days = _days(str(item["start_date"]), str(item["end_date"]))
        used[item["leave_type_id"]] = used.get(item["leave_type_id"], 0) + days
    result = []
    for item in types:
        if not item.get("is_active", True):
            continue
        total = float(item.get("max_days_per_year") or 0)
        result.append({
            "leave_type": item.get("name"),
            "code": item.get("code"),
            "total_days": total,
            "used_days": used.get(item["id"], 0),
            "remaining_days": round(total - used.get(item["id"], 0), 1),
        })
    return {"balances": result, "user": ctx.get("name")}


@tool(
    name="query_my_attendance",
    description="查询本人某月考勤记录与出勤统计，month 格式 YYYY-MM",
    params={"month": "month"},
    roles=("employee", "manager"),
)
def query_my_attendance(ctx: dict, month: str) -> dict[str, Any]:
    with _client(ctx) as client:
        resp = client.get("/api/attendance/my", params={"month": month})
        resp.raise_for_status()
        records = resp.json() or []
    late = sum(1 for r in records if r.get("status") == "late")
    absent = sum(1 for r in records if r.get("status") == "absent")
    return {"month": month, "records": len(records), "late": late, "absent": absent,
            "detail": records[:10]}


@tool(
    name="query_my_salary",
    description="查询本人某月薪资明细（只返回本人，金额脱敏为区间）",
    params={"month": "month"},
    roles=("employee", "manager"),
)
def query_my_salary(ctx: dict, month: str) -> dict[str, Any]:
    with _client(ctx) as client:
        resp = client.get("/api/salary/my", params={"month": month})
        resp.raise_for_status()
        rows = resp.json() or []
    if not rows:
        return {"month": month, "found": False}
    row = rows[0]
    total = float(row.get("total_amount") or row.get("net_amount") or 0)
    return {"month": month, "found": True, "range": f"{int(total // 1000) * 1000}~{int(total // 1000) * 1000 + 999}",
            "status": row.get("status")}


@tool(
    name="submit_leave",
    description="为本人提交请假申请（写操作，需人工确认）",
    params={"leave_type": "str", "start_date": "date", "end_date": "date", "reason": "str"},
    roles=("employee", "manager"),
    write=True,
    requires_confirm=True,
)
def submit_leave(ctx: dict, leave_type: str, start_date: str, end_date: str, reason: str) -> dict[str, Any]:
    days = _days(start_date, end_date)
    with _client(ctx) as client:
        type_item = _resolve_leave_type(client, leave_type)
        # 幂等：同一人、同假种、同日期区间已有待审批记录时，直接返回原单，避免重复提交
        existing = client.get("/api/leave/my").json() or []
        for row in existing:
            if (row.get("status") == "pending"
                    and str(row.get("start_date")) == start_date
                    and str(row.get("end_date")) == end_date
                    and int(row.get("leave_type_id")) == int(type_item["id"])):
                return {"submitted": False, "idempotent": True, "leave_id": row.get("id"),
                        "days": days, "leave_type": type_item.get("name"), "status": row.get("status")}

        payload = {
            "leave_type_id": type_item["id"],
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
        }
        resp = client.post("/api/leave", json=payload)
        resp.raise_for_status()
        data = resp.json() or {}
    return {"submitted": True, "leave_id": data.get("id"), "days": days,
            "leave_type": type_item.get("name"), "status": data.get("status")}


@tool(
    name="list_pending_approvals",
    description="查看待审批的请假申请列表（仅主管）",
    params={},
    roles=("manager",),
)
def list_pending_approvals(ctx: dict) -> dict[str, Any]:
    with _client(ctx) as client:
        resp = client.get("/api/manager/leave/pending")
        resp.raise_for_status()
        rows = resp.json() or []
    return {"count": len(rows), "items": [
        {"id": r.get("id"), "user": r.get("user_name"), "type": r.get("leave_type_name"),
         "start": r.get("start_date"), "end": r.get("end_date"), "days": _days(str(r["start_date"]), str(r["end_date"]))}
        for r in rows[:10]
    ]}


@tool(
    name="approve_leave",
    description="通过某个请假申请（写操作，需人工确认，仅主管）",
    params={"leave_id": "int", "comment": "str"},
    roles=("manager",),
    write=True,
    requires_confirm=True,
)
def approve_leave(ctx: dict, leave_id: int, comment: str) -> dict[str, Any]:
    with _client(ctx) as client:
        pending = client.get("/api/manager/leave/pending").json() or []
        target = next((r for r in pending if int(r.get("id")) == int(leave_id)), None)
        if target is None:
            # 幂等：已经处理过的不再重复审批
            history = client.get("/api/manager/leave/history").json() or []
            old = next((r for r in history if int(r.get("id")) == int(leave_id)), None)
            if old is None:
                return {"approved": False, "not_found": True, "leave_id": leave_id}
            return {"approved": False, "idempotent": True, "leave_id": leave_id,
                    "status": old.get("status")}
        resp = client.put(f"/api/manager/leave/{leave_id}/approve", json={"comment": comment})
        resp.raise_for_status()
        data = resp.json() or {}
    return {"approved": True, "leave_id": leave_id, "status": data.get("status")}
