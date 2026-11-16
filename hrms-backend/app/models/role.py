"""角色 ORM 模型。

role 是一张基础字典表，目前只有 employee、manager 两条数据。
把它独立成表而不是在 user 表中写字符串，是为了让角色具备主键、
可以被外键约束引用，也方便以后扩展更多角色。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    """系统角色，保存 employee 和 manager。"""

    __tablename__ = "role"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[str] = mapped_column(
        # code 是程序判断用的英文标识，name 是界面展示用的中文名称。
        Enum("employee", "manager", name="role_code"),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="role_ref")
