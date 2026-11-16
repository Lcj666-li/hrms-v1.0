"""接口级鉴权与限流测试（用 monkeypatch 替换 token 换用户，不依赖真实 HRMS）。"""

import pytest
from fastapi import HTTPException

from app import main


def _patch_me(monkeypatch, role: str):
    monkeypatch.setattr(main, "_me", lambda token: {"name": "测试", "role": role})


def test_missing_token_returns_401(monkeypatch):
    monkeypatch.setattr(main.config, "DEMO_MODE", False)
    with pytest.raises(HTTPException) as exc:
        main.require_identity(None)
    assert exc.value.status_code == 401


def test_invalid_token_returns_401(monkeypatch):
    def boom(token):
        raise HTTPException(status_code=401, detail="token 无效或已过期")

    monkeypatch.setattr(main, "_me", boom)
    with pytest.raises(HTTPException) as exc:
        main.require_identity("Bearer bad")
    assert exc.value.status_code == 401


def test_employee_cannot_read_stats(monkeypatch):
    _patch_me(monkeypatch, "employee")
    with pytest.raises(HTTPException) as exc:
        main.require_manager(main.require_identity("Bearer t"))
    assert exc.value.status_code == 403


def test_manager_can_read_stats(monkeypatch):
    _patch_me(monkeypatch, "manager")
    identity = main.require_manager(main.require_identity("Bearer t"))
    assert identity["role"] == "manager"


def test_tools_are_filtered_by_role(monkeypatch):
    _patch_me(monkeypatch, "employee")
    names = {item["name"] for item in main.tools("Bearer t")}
    assert "approve_leave" not in names
    assert "query_my_leave_balance" in names


def test_rate_limiter_blocks_after_limit(monkeypatch):
    from app.limits import RateLimiter

    limiter = RateLimiter(max_per_minute=2)
    assert limiter.check("u")[0] is True
    assert limiter.check("u")[0] is True
    allowed, retry = limiter.check("u")
    assert allowed is False and retry > 0
