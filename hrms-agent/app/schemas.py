"""接口数据结构。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Status = Literal["ok", "needs_confirmation", "denied", "blocked", "failed"]


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    why: str = ""


class ChatRequest(BaseModel):
    query: str
    token: str | None = None
    role: str | None = None
    confirmed: bool = False
    session_id: str | None = None


class StepRead(BaseModel):
    index: int
    tool: str
    args: dict[str, Any]
    status: str
    latency_ms: int
    result: Any = None
    error: str | None = None


class ChatResponse(BaseModel):
    status: Status
    answer: str
    session_id: str
    role: str
    steps: list[StepRead] = Field(default_factory=list)
    pending_action: ToolCall | None = None
    verdict: dict[str, Any] | None = None
    total_ms: int = 0
    budget: dict[str, Any] = Field(default_factory=dict)


class ToolInfo(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    roles: list[str]
    write: bool
    requires_confirm: bool
