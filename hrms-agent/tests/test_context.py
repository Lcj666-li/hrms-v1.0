"""相对月份解析测试：确定性改写，不依赖模型。"""

from datetime import date

from app.context import resolve


def _month(offset: int) -> str:
    today = date.today()
    index = today.year * 12 + (today.month - 1) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def test_relative_month_is_replaced():
    text, info = resolve("我上个月迟到几次")
    assert info["month"] == _month(-1)
    assert _month(-1) in text
    assert "上个月" not in text


def test_explicit_month_is_untouched():
    query = "2026-10 的考勤记录看一下"
    text, info = resolve(query)
    assert text == query
    assert info["month"] is None