"""编排层测试：确认闸门、预算闸门、越权拦截（全部离线，不碰网络/数据库）。"""

import dataclasses
import json

import pytest

from app import config, orchestrator
from app.planner import Plan
from app.tools import REGISTRY, get_tool
from app.tools.base import ToolCall


class FakePlanner:
    def __init__(self, calls):
        self._calls = calls

    def plan(self, query, role):
        return Plan(calls=list(self._calls), intent="test", planner="fake")


def _fake_tool(monkeypatch, name, result):
    spec = get_tool(name)
    handler = lambda ctx, **kwargs: result
    monkeypatch.setitem(REGISTRY, name, dataclasses.replace(spec, handler=handler))


@pytest.fixture(autouse=True)
def _offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TRACE_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(orchestrator, "save_trace", lambda trace: True)
    monkeypatch.setattr(orchestrator, "check_write", lambda ctx, call, obs: (True, "", None))


def _ctx(role="employee"):
    return {"role": role, "name": "测试", "token": "t", "base_url": "http://fake"}


def _submit_call():
    return ToolCall(tool="submit_leave", args={
        "leave_type": "年假", "start_date": "2026-12-01",
        "end_date": "2026-12-02", "reason": "test"})


def test_write_stops_at_confirmation():
    orch = orchestrator.Orchestrator(_ctx(), planner=FakePlanner([_submit_call()]))
    trace = orch.run("帮我请 2026-12-01 到 2026-12-02 的年假")
    assert trace.verdict.get("pending_action")
    assert not any(s.status == "ok" for s in trace.steps)


def test_confirmed_write_executes(monkeypatch):
    _fake_tool(monkeypatch, "submit_leave",
               {"submitted": True, "leave_id": 1, "days": 2, "leave_type": "年假", "status": "pending"})
    orch = orchestrator.Orchestrator(_ctx(), planner=FakePlanner([_submit_call()]))
    trace = orch.run("帮我请 2026-12-01 到 2026-12-02 的年假", confirmed=True)
    assert trace.steps[0].status == "ok"
    assert "已提交年假申请" in trace.answer


def test_max_steps_truncates(monkeypatch):
    monkeypatch.setattr(config, "MAX_STEPS", 2)
    _fake_tool(monkeypatch, "query_my_leave_balance", {"balances": []})
    calls = [ToolCall(tool="query_my_leave_balance", args={}) for _ in range(5)]
    orch = orchestrator.Orchestrator(_ctx(), planner=FakePlanner(calls))
    trace = orch.run("查年假")
    assert trace.truncated is True
    assert len(trace.steps) == 2


def test_timeout_stops_execution(monkeypatch):
    monkeypatch.setattr(config, "TIMEOUT_SECONDS", 0)
    _fake_tool(monkeypatch, "query_my_leave_balance", {"balances": []})
    orch = orchestrator.Orchestrator(
        _ctx(), planner=FakePlanner([ToolCall(tool="query_my_leave_balance", args={})]))
    trace = orch.run("查年假")
    assert trace.steps[0].status == "timeout"


def test_denied_is_audited(tmp_path):
    calls = [ToolCall(tool="list_pending_approvals", args={})]
    orch = orchestrator.Orchestrator(_ctx("employee"), planner=FakePlanner(calls))
    trace = orch.run("有哪些待审批的请假？")
    assert trace.verdict.get("denied") is True
    assert trace.steps[0].status == "denied"
    events = [json.loads(line) for line in config.AUDIT_PATH.read_text(encoding="utf-8").splitlines()]
    assert any(e["event"] == "permission_denied" for e in events)