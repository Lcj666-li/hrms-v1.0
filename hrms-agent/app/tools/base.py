"""工具定义与注册表。

设计要点：
1. 每个工具声明可见角色（roles），越权在 guard 层拦截，模型即使选错工具也调不动；
2. 写操作声明 write/requires_confirm，由编排层强制人工确认（HITL）；
3. 参数声明用于生成 function schema，并做调用前校验，避免模型传错参数直接打后端。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

PARAM_TYPES = {"str", "int", "date", "month"}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: dict[str, str]
    roles: tuple[str, ...]
    write: bool = False
    requires_confirm: bool = False
    handler: Callable[..., Any] | None = None

    def info(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "params": self.params,
            "roles": list(self.roles),
            "write": self.write,
            "requires_confirm": self.requires_confirm,
        }


REGISTRY: dict[str, ToolSpec] = {}


def tool(**kwargs) -> Callable:
    """注册工具。"""

    def decorator(fn: Callable) -> Callable:
        spec = ToolSpec(handler=fn, **kwargs)
        if spec.name in REGISTRY:
            raise ValueError(f"工具重名：{spec.name}")
        REGISTRY[spec.name] = spec
        return fn

    return decorator


def get_tool(name: str) -> ToolSpec:
    if name not in REGISTRY:
        raise KeyError(f"未知工具：{name}")
    return REGISTRY[name]


def list_tools(role: str) -> list[ToolSpec]:
    return [spec for spec in REGISTRY.values() if role in spec.roles]


def validate_args(spec: ToolSpec, args: dict) -> None:
    """调用前校验：缺参 / 多参 / 类型。"""
    missing = [k for k in spec.params if k not in args or args[k] in (None, "")]
    if missing:
        raise ValueError(f"工具 {spec.name} 缺少参数：{','.join(missing)}")
    unknown = [k for k in args if k not in spec.params]
    if unknown:
        raise ValueError(f"工具 {spec.name} 收到未知参数：{','.join(unknown)}")
    for key, kind in spec.params.items():
        value = args[key]
        if kind == "int" and not isinstance(value, int):
            raise ValueError(f"参数 {key} 需要 int，实际 {type(value).__name__}")


@dataclass
class ToolCall:
    """一次工具调用：由 Planner 产出，由 Executor 执行。"""

    tool: str
    args: dict = field(default_factory=dict)
    why: str = ""


def to_openai_tool(spec: ToolSpec, max_desc: int = 48) -> dict:
    """把工具声明转成 OpenAI function calling 的 schema。

    为了省 token，参数只给类型不给描述；工具描述截断到 48 字。
    """
    props = {name: {"type": "integer" if kind == "int" else "string"}
             for name, kind in spec.params.items()}
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description[:max_desc],
            "parameters": {"type": "object", "properties": props,
                           "required": list(spec.params.keys())},
        },
    }
