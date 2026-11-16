"""职位 ORM 模型。

position 是部门下的职位字典表，通过 department_id 归属到某个部门。
同一个职位名称可以出现在不同部门（例如两个部门都有“专员”），
但同一个部门内不允许出现两个同名职位。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.user import User


class Position(Base):
    """部门下的具体职位。"""

    __tablename__ = "position"
    __table_args__ = (
        # 联合唯一约束：限制的是“部门 + 职位名”组合，而不是职位名本身。
        UniqueConstraint(
            "department_id",
            "name",
            name="uk_position_department_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("department.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    department: Mapped["Department"] = relationship(
        "Department",
        back_populates="positions",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="position_ref",
    )
