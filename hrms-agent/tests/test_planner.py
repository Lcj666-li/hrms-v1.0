from app.planner import RulePlanner


def test_leave_balance_intent():
    plan = RulePlanner().plan("我还有几天年假", "employee")
    assert plan.intent == "leave_balance"
    assert plan.calls[0].tool == "query_my_leave_balance"


def test_submit_leave_needs_confirm_and_parses_dates():
    plan = RulePlanner().plan("帮我请 2026-12-01 到 2026-12-03 的年假", "employee")
    call = plan.calls[0]
    assert call.tool == "submit_leave"
    assert call.args["start_date"] == "2026-12-01"
    assert call.args["end_date"] == "2026-12-03"
    assert call.args["leave_type"] == "年假"


def test_unknown_query_returns_empty_plan():
    plan = RulePlanner().plan("今天天气怎么样", "employee")
    assert plan.calls == []
