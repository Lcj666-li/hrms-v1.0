"""写操作前置校验：把业务规则从模型手里拿回来。

模型可以"想"提交请假，但"能不能提交"由代码判断：
- 先查余额（必要时自动补一次工具调用，这就是多跳）；
- 余额不足直接拒绝，并给出替代建议；
- 通过后再走人工确认。
"""

from __future__ import annotations

from datetime import datetime

from app.tools.hrms import LEAVE_TYPE_ALIAS, query_my_leave_balance


def _days(start: str, end: str) -> int:
    d1 = datetime.strptime(str(start), "%Y-%m-%d").date()
    d2 = datetime.strptime(str(end), "%Y-%m-%d").date()
    return (d2 - d1).days + 1


def check_write(ctx: dict, call, observations: list[dict]) -> tuple[bool, str, dict | None]:
    """返回 (是否允许, 拒绝原因, 补充观察)。

    observations 是已执行步骤的结果，policy 可以复用，避免重复调用工具。
    """
    if call.tool != "submit_leave":
        return True, "", None

    args = call.args
    need = _days(args["start_date"], args["end_date"])
    leave_code = LEAVE_TYPE_ALIAS.get(str(args["leave_type"]).strip(), str(args["leave_type"]).strip())

    balance = None
    for item in observations:
        data = item.get("result") or {}
        for row in data.get("balances") or []:
            if row.get("code") == leave_code:
                balance = row
                break
        if balance:
            break

    extra = None
    if balance is None:
        # 多跳：写操作前自动补一次余额查询
        fetched = query_my_leave_balance(ctx)
        extra = {"tool": "query_my_leave_balance", "result": fetched, "why": "写操作前置校验"}
        for row in fetched.get("balances") or []:
            if row.get("code") == leave_code:
                balance = row
                break

    if balance is None:
        return True, "", extra   # 查不到就放行，交给人工确认

    remaining = float(balance.get("remaining_days") or 0)
    if remaining < need:
        return False, (
            f"{balance.get('leave_type')}余额不足：剩余 {remaining} 天，申请 {need} 天。"
            f"可以改成请 {remaining} 天{balance.get('leave_type')}，或改用其它假种。"
        ), extra
    return True, "", extra
