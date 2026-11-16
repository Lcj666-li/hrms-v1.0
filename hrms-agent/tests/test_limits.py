"""限流器测试：按用户隔离、60 秒窗口过期、重试建议有界。"""

from app.limits import RateLimiter


def test_keys_are_isolated():
    limiter = RateLimiter(max_per_minute=1)
    assert limiter.check("a")[0] is True
    assert limiter.check("b")[0] is True
    assert limiter.check("a")[0] is False


def test_window_expires(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.limits.time.time", lambda: clock["now"])
    limiter = RateLimiter(max_per_minute=1)
    assert limiter.check("u")[0] is True
    clock["now"] = 1001.0
    assert limiter.check("u")[0] is False
    clock["now"] = 1061.0
    assert limiter.check("u")[0] is True


def test_retry_after_within_window(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.limits.time.time", lambda: clock["now"])
    limiter = RateLimiter(max_per_minute=1)
    limiter.check("u")
    clock["now"] = 1030.0
    allowed, retry = limiter.check("u")
    assert allowed is False
    assert 0 < retry <= 61