"""Agent 服务配置。"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HRMS_BASE_URL = os.getenv("HRMS_BASE_URL", "http://127.0.0.1:8000")
KB_BASE_URL = os.getenv("KB_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
KB_SUBJECT = os.getenv("KB_SUBJECT", "")


def _pick_key() -> str:
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"):
        value = os.getenv(name)
        if value:
            return value
    return ""


LLM_API_KEY = _pick_key()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "4"))
TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT", "20"))
MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "8000"))
# 每个用户每分钟最多请求数（防刷、控成本）
RATE_LIMIT_PER_MINUTE = int(os.getenv("AGENT_RATE_LIMIT", "30"))

# trace 落库（独立库，避免动 HRMS 业务表）
MYSQL_DSN = os.getenv(
    "AGENT_MYSQL_DSN",
    "mysql+pymysql://root:123456@127.0.0.1:3306/hrms_agent?charset=utf8mb4",
)

TRACE_DIR = Path(os.getenv("AGENT_TRACE_DIR", str(BASE_DIR / "traces")))
TRACE_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_PATH = BASE_DIR / "traces" / "audit.jsonl"

# 鉴权：正式模式必须带 JWT；DEMO_MODE 仅用于本地演示与评测
AUTH_REQUIRED = os.getenv("AGENT_AUTH_REQUIRED", "true").lower() in ("1", "true", "yes")
DEMO_MODE = os.getenv("AGENT_DEMO_MODE", "false").lower() in ("1", "true", "yes")

DEMO_ACCOUNTS = {
    "manager": (os.getenv("HRMS_MANAGER_USER", "manager"), os.getenv("HRMS_MANAGER_PASSWORD", "123456")),
    "employee": (os.getenv("HRMS_EMPLOYEE_USER", "employee"), os.getenv("HRMS_EMPLOYEE_PASSWORD", "123456")),
}
