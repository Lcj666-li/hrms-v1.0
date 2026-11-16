"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """登录请求。

    这里故意不加 from_attributes：它是纯输入模型，
    只接收前端传来的 username 和 password 两个字段。
    """

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserBrief(BaseModel):
    """登录返回的精简用户信息。

    只返回 id、name、role 三个前端真正需要的字段，
    避免把手机号、邮箱等个人信息塞进登录响应里。
    role 字段由 User.role 属性提供，对应数据库中的 role_id 关联。
    """

    id: int
    name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """登录成功响应。"""

    access_token: str
    token_type: str = "bearer"
    user: UserBrief
