"""用户资料和员工管理 Pydantic 模型。

同一张 user 表在不同场景下需要不同的字段集合，所以拆成多个模型：
UserRead 用于列表、UserProfileRead 用于个人资料详情、
EmployeeCreate / EmployeeUpdate 用于经理管理员工。
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """用户公共字段。"""

    name: str = Field(min_length=1, max_length=50)
    gender: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class UserRead(UserBase):
    """用户基础信息响应。"""

    id: int
    username: str
    role: str
    role_id: int
    department_id: int | None = None
    position_id: int | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileRead(UserRead):
    """完整个人资料响应。"""

    department: str | None = None
    position: str | None = None
    hire_date: date | None = None


class UserProfileUpdate(BaseModel):
    """员工允许自行修改的个人信息。

    这里刻意不包含 username、role_id、department_id、is_active 等字段：
    员工只能改姓名和联系方式，部门、职位、账号状态由经理维护，
    即使前端伪造了这些字段，FastAPI 也会因为模型中没有定义而直接忽略。
    """

    name: str | None = Field(default=None, min_length=1, max_length=50)
    gender: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class EmployeeCreate(UserBase):
    """经理新增员工请求。

    部门、职位传的是名称字符串而不是 id，后端会自动查字典表，
    不存在时先创建，减少经理端页面的选择成本。
    """

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    department: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    hire_date: date | None = None
    is_active: bool = True


class EmployeeUpdate(BaseModel):
    """经理编辑员工请求，传入 password 时同时重置密码。

    所有字段都是可选的，前端只提交本次修改过的字段，
    后端用 exclude_unset 区分“没传”和“传了空值”。
    """

    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=50)
    gender: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    hire_date: date | None = None
    is_active: bool | None = None


class RoleRead(BaseModel):
    """角色选项响应。"""

    id: int
    code: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentRead(BaseModel):
    """部门选项响应。"""

    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PositionRead(BaseModel):
    """职位选项响应。"""

    id: int
    department_id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)
