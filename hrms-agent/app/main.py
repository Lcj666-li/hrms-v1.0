"""Agent HTTP 服务。

鉴权约定：除 /agent/health 外，所有接口都要求 Authorization: Bearer <token>；
运营类接口（stats / traces）只允许主管角色，避免普通员工看到全量问答记录。
"""

from __future__ import annotations

import json
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.limits import LIMITER
from app.orchestrator import Orchestrator
from app.schemas import ChatRequest, ChatResponse, StepRead, ToolCall
from app.store import get_trace as store_get_trace
from app.store import recent as store_recent
from app.store import stats as store_stats
from app.tools import list_tools

VERSION = "1.0.0"

app = FastAPI(title="HRMS 事务 Agent", version=VERSION,
              description="Planner / Executor 编排，工具级 RBAC + 人工确认")

# 开发期允许 Vite(5173) 直连本服务；生产应改为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _login(username: str, password: str) -> tuple[str, dict]:
    with httpx.Client(base_url=config.HRMS_BASE_URL, timeout=15) as client:
        resp = client.post("/api/auth/login", json={"username": username, "password": password})
        resp.raise_for_status()
        data = resp.json()
    return data["access_token"], {"name": data.get("user", {}).get("name", username)}


def _me(token: str) -> dict:
    """用 token 换当前用户（单独抽出来，方便测试时替换）。"""
    with httpx.Client(base_url=config.HRMS_BASE_URL,
                      headers={"Authorization": f"Bearer {token}"}, timeout=15) as client:
        resp = client.get("/api/auth/me")
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return resp.json()


def require_identity(authorization: str | None) -> dict:
    """所有业务接口的鉴权依赖：必须带有效 token。"""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        if config.DEMO_MODE:
            username, password = config.DEMO_ACCOUNTS["employee"]
            token, _ = _login(username, password)
        else:
            raise HTTPException(status_code=401, detail="缺少 Authorization: Bearer <token>")
    info = _me(token)
    return {"token": token, "name": info.get("name"), "role": info.get("role")}


def require_manager(identity: dict) -> dict:
    if identity.get("role") != "manager":
        raise HTTPException(status_code=403, detail="该接口仅限主管访问")
    return identity


@app.get("/agent/health")
def health() -> dict:
    hrms_ok = False
    try:
        with httpx.Client(base_url=config.HRMS_BASE_URL, timeout=5) as client:
            hrms_ok = client.get("/").status_code == 200
    except Exception:
        hrms_ok = False
    return {"status": "ok" if hrms_ok else "degraded", "version": VERSION, "hrms": hrms_ok,
            "kb": config.KB_BASE_URL, "llm": bool(config.LLM_API_KEY),
            "rate_limit_per_min": config.RATE_LIMIT_PER_MINUTE}


@app.get("/agent/tools")
def tools(authorization: str | None = Header(default=None)) -> list[dict]:
    """按当前登录角色返回可用工具（不再接受客户端自报 role）。"""
    identity = require_identity(authorization)
    return [spec.info() for spec in list_tools(identity["role"])]


@app.post("/agent/chat", response_model=ChatResponse)
def chat(req: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    identity = require_identity(authorization)
    if req.role and req.role != identity["role"]:
        raise HTTPException(status_code=403, detail="请求里的 role 与 token 不一致")

    allowed, retry_after = LIMITER.check(f"{identity['role']}:{identity['name']}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"请求过于频繁，请 {retry_after} 秒后重试",
                            headers={"Retry-After": str(retry_after)})

    ctx = {
        "token": identity["token"], "base_url": config.HRMS_BASE_URL, "role": identity["role"],
        "name": identity["name"], "kb_base_url": config.KB_BASE_URL, "kb_subject": config.KB_SUBJECT,
        "session_id": req.session_id or uuid.uuid4().hex[:12],
    }
    trace = Orchestrator(ctx).run(req.query, confirmed=req.confirmed, session_id=ctx["session_id"])
    if trace.verdict.get("denied"):
        raise HTTPException(status_code=403, detail=trace.verdict.get("deny_reason", "权限不足"))

    pending = trace.verdict.get("pending_action")
    status = "ok"
    if trace.verdict.get("blocked"):
        status = "blocked"
    elif pending:
        status = "needs_confirmation"
    elif all(s.status != "ok" for s in trace.steps) and trace.steps:
        status = "failed"

    response = ChatResponse(
        status=status,
        answer=trace.answer,
        session_id=ctx["session_id"],
        role=identity["role"],
        steps=[StepRead(index=s.index, tool=s.tool, args=s.args, status=s.status,
                        latency_ms=s.latency_ms, result=s.result, error=s.error) for s in trace.steps],
        pending_action=ToolCall(**pending) if pending else None,
        verdict={"intent": trace.verdict.get("intent"), "note": trace.verdict.get("note")},
        total_ms=trace.total_ms,
        budget={"max_steps": config.MAX_STEPS, "timeout_s": config.TIMEOUT_SECONDS,
                "steps_used": len(trace.steps), "truncated": trace.truncated},
    )
    return response


@app.get("/agent/stats")
def stats(days: int = 7, authorization: str | None = Header(default=None)) -> dict:
    """近 N 天运营指标（仅主管）。"""
    require_manager(require_identity(authorization))
    return store_stats(days)


@app.get("/agent/traces")
def traces(limit: int = 20, status: str | None = None,
           authorization: str | None = Header(default=None)) -> list[dict]:
    require_manager(require_identity(authorization))
    return store_recent(limit, status)


@app.get("/agent/traces/{session_id}")
def get_trace(session_id: str, authorization: str | None = Header(default=None)) -> dict:
    """单条明细（仅主管）；优先查库，库里没有回落到 JSON 文件。"""
    require_manager(require_identity(authorization))
    try:
        row = store_get_trace(session_id)
    except Exception:
        row = None
    if row:
        return row
    path = config.TRACE_DIR / f"{session_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="trace 不存在")
    return json.loads(path.read_text(encoding="utf-8"))
