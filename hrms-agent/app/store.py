"""trace 持久化与统计查询（MySQL）。

为什么落库：JSON 文件只能自己看，落库之后才能回答"昨天成功率多少""哪个工具最慢""拦截率趋势"。
库单独建在 hrms_agent，不碰 HRMS 的业务表。
"""

from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlparse

import pymysql

from app import config
from app.trace import Trace

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS agent_trace (
        id VARCHAR(48) PRIMARY KEY,
        session_id VARCHAR(64) NULL,
        query VARCHAR(600) NOT NULL,
        role VARCHAR(16) NOT NULL,
        user_name VARCHAR(64) NULL,
        answer TEXT NULL,
        status VARCHAR(24) NOT NULL,
        planner VARCHAR(24) NULL,
        intent VARCHAR(32) NULL,
        tokens INT NOT NULL DEFAULT 0,
        total_ms INT NOT NULL DEFAULT 0,
        step_count INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        KEY idx_created (created_at),
        KEY idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS agent_trace_step (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        trace_id VARCHAR(48) NOT NULL,
        step_index INT NOT NULL,
        tool VARCHAR(64) NOT NULL,
        status VARCHAR(24) NOT NULL,
        latency_ms INT NOT NULL DEFAULT 0,
        args TEXT NULL,
        result TEXT NULL,
        error VARCHAR(500) NULL,
        KEY idx_trace (trace_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


def _dsn() -> dict:
    parsed = urlparse(config.MYSQL_DSN)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": (parsed.path or "/hrms_agent").lstrip("/") or "hrms_agent",
        "charset": "utf8mb4",
    }


def connect(with_db: bool = True):
    info = _dsn()
    if not with_db:
        info.pop("database", None)
    return pymysql.connect(**info, autocommit=True)


def init_schema() -> None:
    info = _dsn()
    with connect(with_db=False) as conn, conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{info['database']}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
        )
    with connect() as conn, conn.cursor() as cur:
        for ddl in SCHEMA:
            cur.execute(ddl)


def derive_status(trace: Trace) -> str:
    v = trace.verdict or {}
    if v.get("denied"):
        return "denied"
    if v.get("blocked"):
        return "blocked"
    if v.get("pending_action"):
        return "needs_confirmation"
    if any(s.status == "ok" for s in trace.steps):
        return "ok"
    if not trace.steps and trace.answer:
        return "refused"
    return "failed"


def save_trace(trace: Trace) -> bool:
    """写一条 trace；失败只记日志，不影响主流程。"""
    status = derive_status(trace)
    v = trace.verdict or {}
    row = (
        trace.session_id, v.get("session_id"), (trace.query or "")[:600], trace.role,
        trace.user, (trace.answer or "")[:60000], status, v.get("planner"), v.get("intent"),
        int(v.get("tokens") or 0), trace.total_ms, len(trace.steps), datetime.now(),
    )
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO agent_trace (id, session_id, query, role, user_name, answer, status,"
                " planner, intent, tokens, total_ms, step_count, created_at)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                " ON DUPLICATE KEY UPDATE status=VALUES(status),"
                " total_ms=VALUES(total_ms), tokens=VALUES(tokens), step_count=VALUES(step_count),"
                " answer=VALUES(answer)",
                row,
            )
            # 重跑回填时先清掉旧步骤，避免步骤表重复累加
            cur.execute("DELETE FROM agent_trace_step WHERE trace_id = %s", (trace.session_id,))
            for step in trace.steps:
                cur.execute(
                    "INSERT INTO agent_trace_step (trace_id, step_index, tool, status, latency_ms,"
                    " args, result, error) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (trace.session_id, step.index, step.tool, step.status, step.latency_ms,
                     json.dumps(step.args, ensure_ascii=False, default=str)[:4000],
                     json.dumps(step.result, ensure_ascii=False, default=str)[:8000],
                     (step.error or "")[:500] or None),
                )
        return True
    except Exception as exc:  # 数据库不可用不应阻断问答
        print(f"[store] 写入 trace 失败：{type(exc).__name__}: {exc}")
        return False


def _p95(cur, days: int) -> int:
    cur.execute("SELECT COUNT(*) FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY", (days,))
    total = cur.fetchone()[0] or 0
    if not total:
        return 0
    offset = max(0, int(total * 0.95) - 1)
    cur.execute(
        "SELECT total_ms FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY"
        " ORDER BY total_ms ASC LIMIT 1 OFFSET %s", (days, offset))
    row = cur.fetchone()
    return int(row[0]) if row else 0


def stats(days: int = 7) -> dict:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY"
            " GROUP BY status", (days,))
        by_status = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute(
            "SELECT COUNT(*), AVG(total_ms), SUM(tokens), SUM(step_count)"
            " FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY", (days,))
        total, avg_ms, tokens, steps = cur.fetchone()

        cur.execute(
            "SELECT planner, COUNT(*) FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY"
            " GROUP BY planner ORDER BY COUNT(*) DESC", (days,))
        by_planner = [(row[0] or "unknown", row[1]) for row in cur.fetchall()]

        cur.execute(
            "SELECT DATE(created_at) d, COUNT(*), SUM(status='ok'), SUM(status IN ('blocked','denied'))"
            " FROM agent_trace WHERE created_at >= NOW() - INTERVAL %s DAY"
            " GROUP BY d ORDER BY d", (days,))
        by_day = [{"date": str(r[0]), "total": r[1], "ok": int(r[2] or 0), "blocked": int(r[3] or 0)}
                  for r in cur.fetchall()]

        cur.execute(
            "SELECT s.tool, COUNT(*) c, AVG(s.latency_ms) FROM agent_trace_step s"
            " JOIN agent_trace t ON t.id = s.trace_id"
            " WHERE t.created_at >= NOW() - INTERVAL %s DAY GROUP BY s.tool ORDER BY c DESC LIMIT 8",
            (days,))
        top_tools = [{"tool": r[0], "count": r[1], "avg_ms": round(float(r[2] or 0), 1)}
                     for r in cur.fetchall()]

        p95 = _p95(cur, days)

    total = int(total or 0)
    ok = by_status.get("ok", 0)
    return {
        "days": days,
        "total": total,
        "ok": ok,
        "success_rate": round(ok / total, 3) if total else 0,
        "blocked": by_status.get("blocked", 0),
        "denied": by_status.get("denied", 0),
        "needs_confirmation": by_status.get("needs_confirmation", 0),
        "failed": by_status.get("failed", 0),
        "refused": by_status.get("refused", 0),
        "guard_rate": round((by_status.get("blocked", 0) + by_status.get("denied", 0)) / total, 3) if total else 0,
        "avg_ms": round(float(avg_ms or 0), 1),
        "p95_ms": p95,
        "tokens": int(tokens or 0),
        "avg_steps": round(float(steps or 0) / total, 2) if total else 0,
        "by_status": by_status,
        "by_planner": by_planner,
        "by_day": by_day,
        "top_tools": top_tools,
    }


def recent(limit: int = 20, status: str | None = None) -> list[dict]:
    sql = ("SELECT id, session_id, query, role, status, planner, tokens, total_ms,"
           " step_count, created_at FROM agent_trace")
    params: list = []
    if status:
        sql += " WHERE status = %s"
        params.append(status)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [{"id": r[0], "session_id": r[1], "query": r[2], "role": r[3], "status": r[4],
             "planner": r[5], "tokens": r[6], "total_ms": r[7],
             "steps": r[8], "created_at": str(r[9])} for r in rows]


def get_trace(trace_id: str) -> dict | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM agent_trace WHERE id = %s", (trace_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        trace = dict(zip(cols, row))
        cur.execute("SELECT step_index, tool, status, latency_ms, args, result, error"
                    " FROM agent_trace_step WHERE trace_id = %s ORDER BY step_index", (trace_id,))
        trace["steps"] = [
            {"index": r[0], "tool": r[1], "status": r[2], "latency_ms": r[3],
             "args": json.loads(r[4]) if r[4] else {}, "result": json.loads(r[5]) if r[5] else None,
             "error": r[6]}
            for r in cur.fetchall()
        ]
    trace["created_at"] = str(trace.get("created_at"))
    return trace
