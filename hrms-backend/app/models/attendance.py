"""考勤 ORM 模型。

每个员工每天最多一条记录，因此用 (user_id, date) 唯一约束从数据库层面兜底，
防止并发点击打卡按钮时写入两条重复记录。
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Attendance(Base):
    """员工每日考勤记录。"""

    __tablename__ = "attendance"
    __table_args__ = (
        # 唯一约束对应打卡业务规则：一天只能打一次上班卡、一次下班卡。
        UniqueConstraint("user_id", "date", name="uk_attendance_user_date"),
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
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(
        # 状态由后端根据上下班时间自动计算，前端不允许直接传值修改。
        Enum(
            "normal",
            "late",
            "early",
            "late_early",
            "missing",
            "absent",
            name="attendance_status",
        ),
        nullable=False,
        default="missing",
        server_default=text("'missing'"),
        index=True,
    )
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped["User"] = relationship("User", back_populates="attendances")
