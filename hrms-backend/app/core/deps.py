"""FastAPI 通用认证和角色权限依赖。"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User


# tokenUrl 只是 OpenAPI 文档中“获取令牌”的地址，登录接口本身是 JSON 请求。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer Token 中解析当前用户，并校验账号状态。"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        # JWT 的 sub 在编码时是字符串，这里转回数据库主键使用的 int。
        user_id = int(subject)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    # Token 本身可能仍然有效，但账号可能已被经理禁用，因此必须查库确认状态。
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    return user


def require_employee(
    current_user: User = Depends(get_current_user),
) -> User:
    """仅允许员工访问。"""

    # 依赖链：先通过 get_current_user 验证 Token，再判断角色代码。
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该接口仅限员工访问",
        )
    return current_user


def require_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    """仅允许经理访问。"""

    if current_user.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该接口仅限经理访问",
        )
    return current_user
