import pytest

from app.guard import PermissionDenied, check
from app.tools import get_tool


def test_employee_cannot_use_manager_tool(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "audit.jsonl")
    spec = get_tool("list_pending_approvals")
    with pytest.raises(PermissionDenied):
        check(spec, "employee", {}, {"name": "员工"})
    assert "permission_denied" in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_manager_can_use_manager_tool():
    check(get_tool("list_pending_approvals"), "manager", {}, {"name": "经理"})


def test_employee_can_use_shared_tool():
    check(get_tool("query_my_leave_balance"), "employee", {}, {"name": "员工"})
