"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    attendance,
    auth,
    leave,
    leave_type,
    manager,
    notice,
    salary,
)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 FastAPI + Vue 3 的人事管理系统后端接口",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 前端开发服务器地址从 .env 读取，默认允许 Vite 的 5173 端口。
# 生产环境应只允许真实前端域名，避免任意网站调用后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 认证接口：登录、获取当前用户
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])

# 个人资料接口写在 auth.py 中，但使用独立的 /api/user 前缀
app.include_router(auth.user_router, prefix="/api/user", tags=["个人资料"])

# 员工端业务接口
app.include_router(
    attendance.router,
    prefix="/api/attendance",
    tags=["考勤"],
)
app.include_router(leave.router, prefix="/api/leave", tags=["请假"])
app.include_router(
    leave_type.router,
    prefix="/api/leave-types",
    tags=["请假类型"],
)
app.include_router(notice.router, prefix="/api/notice", tags=["公告"])
app.include_router(
    salary.router,
    prefix="/api/salary",
    tags=["薪资"],
)

# 经理端接口
app.include_router(
    manager.router,
    prefix="/api/manager",
    tags=["经理端"],
)
app.include_router(
    leave_type.manager_router,
    prefix="/api/manager/leave-types",
    tags=["经理端-请假类型"],
)
app.include_router(
    salary.manager_router,
    prefix="/api/manager/salary",
    tags=["经理端-薪资"],
)


@app.get("/", tags=["系统"])
def root() -> dict[str, str]:
    """服务根路径，用于快速确认后端已启动。"""

    return {
        "message": "HRMS 后端服务运行中",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["系统"])
def health_check() -> dict[str, str]:
    """健康检查接口。"""

    return {"status": "ok"}
