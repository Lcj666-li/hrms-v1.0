"""相对月份解析：把"这个月/上个月/下个月"补全成具体 YYYY-MM。

只做确定性的文本改写（不需要模型，成本为零），规则/LLM Planner 都能直接用。
"""

from __future__ import annotations

import re
from datetime import date

MONTH_WORDS = {
    "这个月": 0, "本月": 0, "当月": 0,
    "上个月": -1, "上月": -1,
    "下个月": 1, "下月": 1,
}


def _shift_month(offset: int) -> str:
    today = date.today()
    index = today.year * 12 + (today.month - 1) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_offset(text: str) -> int | None:
    for word, offset in MONTH_WORDS.items():
        if word in text:
            return offset
    return None


def resolve(query: str) -> tuple[str, dict]:
    """返回 (补全后的问题, 解析信息)。"""
    text = (query or "").strip()
    info: dict = {"original": text, "month": None}

    if not text:
        return text, info

    offset = month_offset(text)
    if offset is not None and not re.search(r"20\d{2}-\d{2}", text):
        month = _shift_month(offset)
        info["month"] = month
        for word in MONTH_WORDS:
            text = text.replace(word, month)
        info["replaced"] = True

    return text, info