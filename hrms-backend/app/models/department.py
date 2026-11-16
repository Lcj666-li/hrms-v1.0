"""部门 ORM 模型。

department 是部门字典表，员工通过 user.department_id 关联到具体部门。
经理端按部门筛选考勤、员工列表展示部门名称都依赖这张表。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.position import Position
    from app.models.user import User


class Department(Base):
    """企业部门信息。"""

    __tablename__ = "department"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        # 部门名称唯一，避免出现两个同名部门导致筛选结果混乱。
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    positions: Mapped[list["Position"]] = relationship(
        "Position",
        back_populates="department",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="department_ref",
    )
