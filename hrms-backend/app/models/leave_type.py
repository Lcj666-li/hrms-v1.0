"""请假类型 ORM 模型。

请假类型把原来写在请假申请里的“事假、病假、年假”等分类抽成字典表，
便于经理统一维护名称、是否带薪、年度天数和是否需要审批。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.leave import LeaveRequest


class LeaveType(Base):
    """请假类型字典。"""

    __tablename__ = "leave_type"
    __table_args__ = (
        UniqueConstraint("code", name="uk_leave_type_code"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="类型代码，例如 annual、sick、personal",
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    max_days_per_year: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1),
        nullable=True,
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest",
        back_populates="leave_type",
    )
