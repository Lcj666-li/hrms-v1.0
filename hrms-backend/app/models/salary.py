"""薪资记录 ORM 模型。

一条薪资记录对应“某位员工某个月”的工资单。实发工资由后端根据
基本工资、奖金和各项扣款统一计算，接口不直接信任前端提交的实发金额。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SalaryRecord(Base):
    """员工月度薪资记录。"""

    __tablename__ = "salary_record"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "salary_month",
            name="uk_salary_user_month",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    salary_month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
        comment="薪资月份，格式 YYYY-MM",
    )
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0.00"),
    )
    attendance_deduction: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    leave_deduction: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    social_security: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    actual_salary: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0.00"),
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "issued", name="salary_status"),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="salary_records",
        foreign_keys=[user_id],
    )
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_salary_records",
        foreign_keys=[created_by],
    )
