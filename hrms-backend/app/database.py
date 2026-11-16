"""SQLAlchemy 数据库连接与会话管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


# PyMySQL 在长时间空闲后可能断开连接，因此开启连接前检测与连接回收。
# pool_pre_ping 会先探测连接是否可用，pool_recycle 则定期换掉旧连接，
# 这两个配置可以显著减少 MySQL "server has gone away" 类错误。
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# 每个请求创建一个 Session，避免多个请求共享同一个事务上下文。
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    # 提交后不过期 ORM 对象，便于提交后直接读取属性生成响应。
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """为每个请求创建一个数据库会话，请求结束后自动关闭。"""

    db = SessionLocal()
    try:
        # FastAPI 依赖会在请求处理完成后回到这里执行 finally。
        yield db
    finally:
        db.close()
