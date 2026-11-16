# HRMS 人事管理系统 + 事务智能助手

自研人事系统（9 张业务表）与跑在其上的事务 Agent，前后端分离：

| 模块 | 技术 | 端口 | 说明 |
|---|---|---|---|
| `hrms-backend` | FastAPI + SQLAlchemy + MySQL | 8000 | 员工 / 考勤 / 薪资 / 请假 / 审批 / 公告，JWT 鉴权 |
| `hrms-frontend` | Vue3 + TypeScript + Element Plus | 5173 | 员工端 + 管理端 + AI 助手抽屉 + Agent 运营面板 |
| `hrms-agent` | FastAPI + DeepSeek Function Calling | 8010 | 7 个业务工具，规则 + LLM 混合规划，写操作人工确认 |

## 启动顺序

```bash
# 1) 后端：初始化 MySQL（建表脚本在 hrms-backend/sql），配置 .env 后
cd hrms-backend && python run.py

# 2) Agent：配置 .env（LLM key 可留空走规则模式）
cd hrms-agent && python run.py

# 3) 前端
cd hrms-frontend && npm install && npm run dev
```

打开 http://localhost:5173 ，演示账号 `employee / 123456`、`manager / 123456`
（可用 `hrms-agent/scripts/seed_demo_data.py` 生成演示数据）。

各模块的配置项见对应目录的 `.env.example`；Agent 的设计与测试说明见
[hrms-agent/README.md](hrms-agent/README.md)。