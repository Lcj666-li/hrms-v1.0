"""用户 ORM 模型。

系统采用“单用户表 + 角色外键”的设计：
经理和员工都是 user 表中的一行，通过 role_id 指向 role 表区分身份。
这样登录、请假审批、公告发布等逻辑都只需要操作同一种用户对象。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.department import Department
    from app.models.leave import LeaveRequest
    from app.models.notice import Notice
    from app.models.position import Position
    from app.models.role import Role
    from app.models.salary import SalaryRecord


class User(Base):
    """系统用户，经理和员工共用一张表。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        # RESTRICT：角色被用户引用时不允许删除，防止出现“没有角色的用户”。
        ForeignKey("role.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        # SET NULL：部门被删除时把员工的部门置空即可，不连带删除员工账号。
        ForeignKey("department.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    position_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("position.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance",
        back_populates="user",
    )
    # 请假表有两个指向 user 的外键：申请人 user_id 和审批人 approver_id，
    # 因此必须用 foreign_keys 明确告诉 SQLAlchemy 各自对应哪一条关系，
    # 否则它会因无法判断外键而报 AmbiguousForeignKeysError。
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest",
        back_populates="user",
        foreign_keys="LeaveRequest.user_id",
    )
    approved_leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest",
        back_populates="approver",
        foreign_keys="LeaveRequest.approver_id",
    )
    # 薪资表同样有 user_id 和 created_by 两个指向 user 的外键，
    # 必须分别声明 foreign_keys，避免 SQLAlchemy 无法确定关系方向。
    salary_records: Mapped[list["SalaryRecord"]] = relationship(
        "SalaryRecord",
        back_populates="user",
        foreign_keys="SalaryRecord.user_id",
    )
    created_salary_records: Mapped[list["SalaryRecord"]] = relationship(
        "SalaryRecord",
        back_populates="creator",
        foreign_keys="SalaryRecord.created_by",
    )
    notices: Mapped[list["Notice"]] = relationship(
        "Notice",
        back_populates="author",
    )
    role_ref: Mapped["Role"] = relationship("Role", back_populates="users")
    department_ref: Mapped["Department | None"] = relationship(
        "Department",
        back_populates="users",
    )
    position_ref: Mapped["Position | None"] = relationship(
        "Position",
        back_populates="users",
    )

    @property
    def role(self) -> str:
        """向前端输出角色代码（employee / manager）。

        role 在数据库中是 role_id 外键，这里用只读属性把它转换成角色代码，
        前端拿到的 JSON 结构和“直接在 user 表存 role 字段”的方案完全一致，
        后续即使再增加角色也不需要改动前端判断逻辑。
        """

        return self.role_ref.code if self.role_ref else ""

    @property
    def department(self) -> str | None:
        """向前端输出部门名称（数据库存的是 department_id）。"""

        return self.department_ref.name if self.department_ref else None

    @property
    def position(self) -> str | None:
        """向前端输出职位名称（数据库存的是 position_id）。"""

        return self.position_ref.name if self.position_ref else None
