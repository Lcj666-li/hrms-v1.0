"""制度问答工具：转调知擎知识库服务的检索接口。

Agent 不重复实现检索——把知识能力当成一个外部服务来调用，
这也是真实系统里"能力服务化、编排在上层"的做法。知识服务不可用时降级为 None。
"""

from __future__ import annotations

import httpx

from app.tools.base import tool

# 进程内缓存 + 超时：知识库冷启动时单次可能到 10s，不设上限会把 P95 拖垮
_CACHE: dict[str, dict] = {}
_TIMEOUT = 8.0


@tool(
    name="search_policy",
    description="查询公司制度（年假规则、报销规定、考勤制度等），返回答案与引用来源",
    params={"question": "str"},
    roles=("employee", "manager"),
)
def search_policy(ctx: dict, question: str) -> dict:
    base = ctx.get("kb_base_url") or ""
    if not base:
        return {"available": False, "answer": None, "sources": []}
    cached = _CACHE.get(question)
    if cached is not None:
        return cached
    payload = {"query": question}
    if ctx.get("kb_subject"):
        payload["subject"] = ctx["kb_subject"]
    try:
        with httpx.Client(base_url=base, timeout=30) as client:
            resp = client.post("/api/v1/qa/ask", json=payload, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return {"available": False, "answer": None, "sources": []}
            data = resp.json() or {}
    except Exception:
        return {"available": False, "answer": None, "sources": []}
    sources = data.get("sources") or []
    result = {
        "available": True,
        "answer": data.get("answer"),
        "is_streaming": data.get("is_streaming", False),
        "sources": [{"index": s.get("index"), "title": s.get("title"), "subject": s.get("subject")}
                    for s in sources[:3]],
    }
    if len(_CACHE) < 50:
        _CACHE[question] = result
    return result
