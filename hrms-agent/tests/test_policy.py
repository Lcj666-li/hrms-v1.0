from app.policies import check_write
from app.tools.base import ToolCall


def _call(days_start="2026-12-01", days_end="2026-12-02", leave_type="年假"):
    return ToolCall(tool="submit_leave",
                    args={"leave_type": leave_type, "start_date": days_start,
                          "end_date": days_end, "reason": "test"})


def _obs(remaining, code="annual", name="年假"):
    return [{"result": {"balances": [{"code": code, "leave_type": name,
                                      "total_days": 10, "used_days": 10 - remaining,
                                      "remaining_days": remaining}]}}]


def test_balance_enough_allows():
    ok, reason, extra = check_write({}, _call(), _obs(5))
    assert ok is True
    assert reason == ""
    assert extra is None


def test_balance_short_blocks():
    ok, reason, _ = check_write({}, _call("2026-12-01", "2026-12-05"), _obs(2))
    assert ok is False
    assert "余额不足" in reason
    assert "2" in reason


def test_non_write_tool_passthrough():
    call = ToolCall(tool="query_my_leave_balance", args={})
    ok, reason, extra = check_write({}, call, [])
    assert ok is True and reason == "" and extra is None
