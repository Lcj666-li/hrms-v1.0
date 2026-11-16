"""开发环境启动入口。

直接运行这个文件即可启动后端（不需要记 uvicorn 的命令行参数）。
reload=settings.DEBUG 表示开发模式下修改代码会自动重启服务，
正式部署时把 .env 中的 DEBUG 改成 false 即可关闭自动重载。
"""

import uvicorn

from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
