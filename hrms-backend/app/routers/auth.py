"""认证接口与员工个人资料接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_employee
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserBrief
from app.schemas.user import UserProfileRead, UserProfileUpdate


router = APIRouter()
user_router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """用户登录并签发 JWT。"""

    # 这里不需要区分“用户不存在”和“密码错误”，统一返回相同提示，
    # 避免攻击者通过错误信息枚举系统中存在的用户名。
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    token = create_access_token(
        # 只把必要身份信息写进 JWT；权限仍以后端数据库中的最新数据为准。
        subject=user.id,
        role=user.role,
        name=user.name,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserBrief.model_validate(user),
    )


@router.get("/me", response_model=UserBrief)
def get_me(current_user: User = Depends(get_current_user)) -> UserBrief:
    """获取当前登录用户的基本信息。"""

    return UserBrief.model_validate(current_user)


@user_router.get("/profile", response_model=UserProfileRead)
def get_profile(
    current_user: User = Depends(require_employee),
) -> UserProfileRead:
    """员工查看自己的完整资料。"""
    return UserProfileRead.model_validate(current_user)


@user_router.put("/profile", response_model=UserProfileRead)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    """员工修改允许自助维护的个人信息。"""

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="姓名不能为空",
        )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return UserProfileRead.model_validate(current_user)
