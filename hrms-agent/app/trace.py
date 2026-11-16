"""每步 trace：谁、用哪个工具、什么参数、多久、结果如何。

没有 trace 的 Agent 无法排错——失败到底是"规划错"还是"工具错"根本分不清。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app import config


@dataclass
class Step:
    index: int
    tool: str
    args: dict
    status: str
    latency_ms: int
    result: object = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "index": self.index, "tool": self.tool, "args": self.args,
            "status": self.status, "latency_ms": self.latency_ms,
            "result": self.result, "error": self.error,
        }


@dataclass
class Trace:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    role: str = ""
    user: str = ""
    started_at: float = field(default_factory=time.time)
    steps: list[Step] = field(default_factory=list)
    answer: str = ""
    verdict: dict = field(default_factory=dict)
    truncated: bool = False

    def add(self, tool: str, args: dict, status: str, latency_ms: int,
            result=None, error: str | None = None) -> Step:
        step = Step(len(self.steps) + 1, tool, args, status, latency_ms, result, error)
        self.steps.append(step)
        return step

    @property
    def total_ms(self) -> int:
        return int((time.time() - self.started_at) * 1000)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id, "query": self.query, "role": self.role,
            "user": self.user, "answer": self.answer, "verdict": self.verdict,
            "truncated": self.truncated, "total_ms": self.total_ms,
            "steps": [s.to_dict() for s in self.steps],
            "ts": datetime.now().isoformat(timespec="seconds"),
        }

    def save(self) -> None:
        path = config.TRACE_DIR / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
