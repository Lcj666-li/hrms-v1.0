"""SQLAlchemy ORM 模型统一导出。

app/main.py 只导入这个包，就能让全部模型注册到 Base.metadata 中，
否则 Base.metadata.create_all() 会漏建没有被导入过的表。
另外，字符串形式的 relationship（如 "User"）也需要所有类都已加载才能解析，
统一在这里导入可以避免模型之间的循环引用问题。
"""

from app.models.attendance import Attendance
from app.models.department import Department
from app.models.leave import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.notice import Notice
from app.models.position import Position
from app.models.role import Role
from app.models.salary import SalaryRecord
from app.models.user import User

__all__ = [
    "Role",
    "Department",
    "Position",
    "User",
    "Attendance",
    "LeaveType",
    "LeaveRequest",
    "SalaryRecord",
    "Notice",
]
