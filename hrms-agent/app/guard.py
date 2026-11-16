"""工具级权限（RBAC）与越权审计。

模型可能"选错工具"，也可能被提示词注入诱导去查别人薪资。
所以权限判断不能交给模型，必须在执行前用角色硬校验，并落审计日志。
"""

from __future__ import annotations

import json
from datetime import datetime

from app import config
from app.tools.base import ToolSpec


class PermissionDenied(Exception):
    """越权调用：直接拒绝，不执行工具。"""


def audit(event: dict) -> None:
    event = {"ts": datetime.now().isoformat(timespec="seconds"), **event}
    with open(config.AUDIT_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def check(spec: ToolSpec, role: str, args: dict, user: dict) -> None:
    if role in spec.roles:
        return
    audit({"event": "permission_denied", "role": role, "user": user.get("name"),
           "tool": spec.name, "args": args, "allowed_roles": list(spec.roles)})
    raise PermissionDenied(
        f"当前角色（{role}）无权调用工具 {spec.name}，该操作仅限 {'/'.join(spec.roles)}"
    )
