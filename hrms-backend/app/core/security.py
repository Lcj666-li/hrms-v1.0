"""密码加密与 JWT 令牌工具。

这个模块只负责“密码怎么存”和“令牌怎么签发、怎么解析”两件事，
不涉及数据库查询和权限判断，这样认证逻辑可以复用在登录、注册、改密等多个场景。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# bcrypt 是专门为密码设计的慢哈希算法：同样密码每次加盐结果都不同，
# 即使数据库泄露，攻击者也无法通过彩虹表批量还原明文密码。
# deprecated="auto" 表示以后换成更强算法时，旧哈希仍可校验并自动升级。
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与数据库中的 bcrypt 哈希是否匹配。

    注意：永远不要把用户输入的密码加密后和数据库字段做字符串比较，
    因为 bcrypt 每次生成的盐不同，必须用 verify 让算法自己解析盐值再比对。
    """

    return pwd_context.verify(plain_password, password_hash)


def get_password_hash(password: str) -> str:
    """生成 bcrypt 密码哈希，用于新增员工和重置密码。"""

    return pwd_context.hash(password)


def create_access_token(
    subject: int | str,
    role: str,
    name: str,
    expires_delta: timedelta | None = None,
) -> str:
    """签发 JWT，sub 保存用户 ID，默认有效期 24 小时。

    载荷中同时保存 role 和 name，是为了让前端登录后无需再查一次数据库
    就能显示用户名并按角色跳转；但后端鉴权不会只信任令牌里的 role，
    仍然会回查数据库确认账号是否被禁用（见 app/core/deps.py）。
    """

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "name": name,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """解析并校验 JWT，失败时抛出 ValueError。"""

    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("无效或已过期的令牌") from exc
