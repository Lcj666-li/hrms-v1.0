"""极简 OpenAI 兼容客户端（只用 httpx，不引入额外 SDK）。

支持 function calling；返回 (message, usage)，调用方负责解析 tool_calls。
"""

from __future__ import annotations

from typing import Any

import httpx

from app import config


class LLMError(RuntimeError):
    """LLM 调用失败（网络/鉴权/格式），调用方应降级。"""


def chat(messages: list[dict], tools: list[dict] | None = None,
         temperature: float = 0.0, max_tokens: int = 512) -> tuple[dict, dict]:
    if not config.LLM_API_KEY:
        raise LLMError("未配置 LLM_API_KEY")

    payload: dict[str, Any] = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        resp = httpx.post(
            config.LLM_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json=payload,
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise LLMError(f"网络错误：{exc}") from exc

    if resp.status_code != 200:
        raise LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"响应格式异常：{data}") from exc
    return message, data.get("usage") or {}
