from app.tools import get_tool, list_tools, validate_args


def test_registry_has_core_tools():
    names = {spec.name for spec in list_tools("employee")}
    assert {"query_my_leave_balance", "query_my_attendance", "submit_leave"} <= names


def test_manager_only_tools_hidden_from_employee():
    names = {spec.name for spec in list_tools("employee")}
    assert "list_pending_approvals" not in names
    assert "approve_leave" not in names


def test_validate_args_rejects_missing_and_unknown():
    spec = get_tool("submit_leave")
    for bad in ({"leave_type": "年假"}, {"leave_type": "年假", "start_date": "2026-12-01",
                                        "end_date": "2026-12-02", "reason": "x", "extra": 1}):
        try:
            validate_args(spec, bad)
        except ValueError:
            continue
        raise AssertionError(f"应当拒绝：{bad}")


def test_write_tools_require_confirm():
    assert get_tool("submit_leave").requires_confirm is True
    assert get_tool("approve_leave").requires_confirm is True
    assert get_tool("query_my_leave_balance").requires_confirm is False


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class _FakeClient:
    """按 URL 返回预设数据，并记录写请求，用于验证幂等时不发写请求。"""

    def __init__(self, routes):
        self.routes = routes
        self.writes = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None):
        return _FakeResponse(self.routes.get(url, []))

    def post(self, url, json=None):
        self.writes.append(("POST", url))
        return _FakeResponse({"id": 99, "status": "pending"})

    def put(self, url, json=None):
        self.writes.append(("PUT", url))
        return _FakeResponse({"status": "approved"})


def test_submit_leave_idempotent_on_same_pending(monkeypatch):
    from app.tools import hrms

    fake = _FakeClient({
        "/api/leave-types": [{"id": 1, "code": "annual", "name": "年假"}],
        "/api/leave/my": [{"id": 7, "status": "pending", "leave_type_id": 1,
                           "start_date": "2026-12-01", "end_date": "2026-12-02"}],
    })
    monkeypatch.setattr(hrms, "_client", lambda ctx, timeout=15.0: fake)
    result = hrms.submit_leave({}, "年假", "2026-12-01", "2026-12-02", "test")
    assert result["idempotent"] is True
    assert result["leave_id"] == 7
    assert fake.writes == []


def test_approve_leave_idempotent_on_processed(monkeypatch):
    from app.tools import hrms

    fake = _FakeClient({
        "/api/manager/leave/pending": [],
        "/api/manager/leave/history": [{"id": 5, "status": "approved"}],
    })
    monkeypatch.setattr(hrms, "_client", lambda ctx, timeout=15.0: fake)
    result = hrms.approve_leave({}, 5, "同意")
    assert result["idempotent"] is True
    assert result["approved"] is False
    assert fake.writes == []
