"""答案渲染测试。"""


def test_render_approve_idempotent_message():
    from app.orchestrator import _render
    from app.trace import Trace

    trace = Trace(query="通过请假单 9", role="manager", user="经理")
    trace.add("approve_leave", {"leave_id": 9}, "ok", 10,
              result={"approved": False, "idempotent": True, "leave_id": 9, "status": "approved"})
    text = _render(trace)
    assert "未重复审批" in text
    assert "已通过请假单" not in text


def test_render_approve_success_message():
    from app.orchestrator import _render
    from app.trace import Trace

    trace = Trace(query="通过请假单 9", role="manager", user="经理")
    trace.add("approve_leave", {"leave_id": 9}, "ok", 10,
              result={"approved": True, "leave_id": 9, "status": "approved"})
    assert "已通过请假单 #9" in _render(trace)
