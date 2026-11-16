"""请假申请 ORM 模型。

一条记录同时保存申请信息（开始/结束日期、事由）和审批信息
（审批人、审批意见、审批时间），因此员工提交后经理可以直接在原记录上审批，
不需要再建一张审批流水表。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.leave_type import LeaveType
    from app.models.user import User


class LeaveRequest(Base):
    """员工请假申请及审批结果。"""

    __tablename__ = "leave_request"
    __table_args__ = (
        # 数据库层再校验一次日期区间，防止绕过接口校验写入非法数据。
        CheckConstraint("end_date >= start_date", name="chk_leave_date_range"),
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
    leave_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "leave_type.id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "approved",
            "rejected",
            "cancelled",
            name="leave_status",
        ),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    approver_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    approve_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    approve_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="leave_requests",
        foreign_keys=[user_id],
    )
    leave_type: Mapped["LeaveType"] = relationship(
        "LeaveType",
        back_populates="leave_requests",
    )
    approver: Mapped["User | None"] = relationship(
        "User",
        back_populates="approved_leave_requests",
        foreign_keys=[approver_id],
    )
