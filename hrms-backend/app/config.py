"""应用配置。

所有可变配置优先从 hrms-backend/.env 读取，未配置时使用安全的本地默认值。

把配置集中在这个文件的原因：
1. 数据库地址、JWT 密钥、跨域白名单等参数会随电脑环境变化，写死在业务代码里
   会导致换一台电脑就要改多处代码；
2. 密钥属于敏感信息，放在 .env 中可以避免被提交到代码仓库；
3. 业务模块统一通过 settings 对象取值，修改配置时只需要改一个地方。
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# .env 位于 hrms-backend 根目录，config.py 位于 app 目录，因此向上一级定位。
# 使用绝对路径的好处是：不管从哪个目录启动 run.py，都能找到同一个 .env 文件。
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """项目运行配置。"""

    APP_NAME: str = os.getenv("APP_NAME", "HRMS 人事管理系统")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:123456@127.0.0.1:3306/hrms?charset=utf8mb4",
    )
    # 连接串格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?字符集
    # charset=utf8mb4 用于支持中文和 emoji，避免姓名、公告内容出现乱码。

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "hrms-change-this-secret-key-in-production",
    )
    # JWT 密钥用于签名和验签。只要密钥不同，别人伪造的令牌就无法通过校验。
    # 默认值只方便本地运行，正式部署必须改成随机长字符串。
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(24 * 60))
    )
    # 24 * 60 分钟 = 24 小时，与需求中的“令牌 24 小时过期”一致。

    # 前后端分离时浏览器会先发 OPTIONS 预检请求，后端必须显式允许前端地址访问。
    # localhost 和 127.0.0.1 在浏览器看来是两个不同的来源，所以两个都要写。
    BACKEND_CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
