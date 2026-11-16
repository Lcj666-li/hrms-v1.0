"""把 traces/*.json 回填进 MySQL（历史数据不丢）。

    python scripts/backfill_traces.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import config  # noqa: E402
from app.store import init_schema, save_trace  # noqa: E402
from app.trace import Step, Trace  # noqa: E402


def load(path: Path) -> Trace:
    data = json.loads(path.read_text(encoding="utf-8"))
    trace = Trace(session_id=data.get("session_id") or path.stem,
                  query=data.get("query", ""), role=data.get("role", ""),
                  user=data.get("user", ""))
    # 还原原始耗时（Trace.total_ms 由 started_at 推算）
    import time
    trace.started_at = time.time() - float(data.get("total_ms") or 0) / 1000.0
    trace.answer = data.get("answer", "")
    trace.verdict = data.get("verdict") or {}
    trace.truncated = bool(data.get("truncated"))
    for item in data.get("steps") or []:
        trace.steps.append(Step(
            index=item.get("index", 0), tool=item.get("tool", ""), args=item.get("args") or {},
            status=item.get("status", "ok"), latency_ms=item.get("latency_ms", 0),
            result=item.get("result"), error=item.get("error"),
        ))
    return trace


def main() -> int:
    init_schema()
    files = sorted(config.TRACE_DIR.glob("*.json"))
    ok = 0
    for path in files:
        try:
            if save_trace(load(path)):
                ok += 1
        except Exception as exc:
            print("跳过", path.name, type(exc).__name__, exc)
    print(f"回填完成：{ok}/{len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
