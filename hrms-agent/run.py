"""启动入口。

    python run.py            # 起服务（默认 8010）
    python run.py --selfcheck  # 用演示账号跑一遍工具与编排（不需要 LLM）
"""

from __future__ import annotations

import json
import sys

import httpx

from app import config
from app.main import _login
from app.orchestrator import Orchestrator


CASES = [
    ("employee", "我还有几天年假？"),
    ("employee", "这个月我迟到几次？"),
    ("employee", "这个月工资发了吗？"),
    ("manager", "有哪些待审批的请假？"),
    ("employee", "上个月工资发了吗？"),
    ("employee", "公司年假制度是怎么规定的？"),
]


def _ctx(role: str) -> dict:
    username, password = config.DEMO_ACCOUNTS[role]
    token, info = _login(username, password)
    return {"token": token, "base_url": config.HRMS_BASE_URL, "role": role,
            "name": info.get("name"), "kb_base_url": config.KB_BASE_URL, "kb_subject": config.KB_SUBJECT}


def selfcheck() -> int:
    failed = 0
    for role, query in CASES:
        ctx = _ctx(role)
        trace = Orchestrator(ctx).run(query)
        ok = bool(trace.steps) and all(s.status == "ok" for s in trace.steps)
        failed += 0 if ok else 1
        print(f"[{'OK ' if ok else 'FAIL'}] {role:8s} {query}")
        print(f"       意图={trace.verdict.get('intent')} 步数={len(trace.steps)} "
              f"耗时={trace.total_ms}ms")
        print(f"       回答={trace.answer[:90]}")
    print(f"\n完成：{len(CASES) - failed}/{len(CASES)} 通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        raise SystemExit(selfcheck())
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8010, reload=False)
