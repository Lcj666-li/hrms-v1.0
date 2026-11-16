"""Pydantic 请求与响应模型统一导出。

Schema 层负责“接口长什么样”：
1. 请求模型限制字段长度、类型和取值，非法参数在进入业务代码前就被 FastAPI 拦下；
2. 响应模型决定哪些字段会返回给前端，password_hash 永远不会出现在响应里；
3. 路由文件只导入这里导出的名字，不用关心模型具体定义在哪个文件。
"""

from app.schemas.attendance import (
    AttendanceCheckResponse,
    AttendanceRead,
    AttendanceStat,
)
from app.schemas.auth import LoginRequest, LoginResponse, UserBrief
from app.schemas.leave import (
    LeaveCancelResponse,
    LeaveCreate,
    LeaveRead,
    LeaveReview,
)
from app.schemas.leave_type import (
    LeaveTypeCreate,
    LeaveTypeRead,
    LeaveTypeUpdate,
)
from app.schemas.notice import NoticeCreate, NoticeRead, NoticeUpdate
from app.schemas.salary import SalaryCreate, SalaryRead, SalaryUpdate
from app.schemas.user import (
    DepartmentRead,
    EmployeeCreate,
    EmployeeUpdate,
    PositionRead,
    RoleRead,
    UserProfileRead,
    UserProfileUpdate,
    UserRead,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "UserBrief",
    "UserRead",
    "UserProfileRead",
    "UserProfileUpdate",
    "RoleRead",
    "DepartmentRead",
    "PositionRead",
    "EmployeeCreate",
    "EmployeeUpdate",
    "AttendanceRead",
    "AttendanceCheckResponse",
    "AttendanceStat",
    "LeaveCreate",
    "LeaveRead",
    "LeaveReview",
    "LeaveCancelResponse",
    "LeaveTypeCreate",
    "LeaveTypeUpdate",
    "LeaveTypeRead",
    "SalaryCreate",
    "SalaryUpdate",
    "SalaryRead",
    "NoticeCreate",
    "NoticeUpdate",
    "NoticeRead",
]
