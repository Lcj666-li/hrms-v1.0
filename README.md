<div align="center">

# HRMS 人事管理系统 + 事务 Agent

**前后端分离的自研 HRMS，上面跑一个能真办业务的事务 Agent**

`FastAPI` · `SQLAlchemy + MySQL 8` · `Vue 3 + TypeScript + Element Plus` · `Function Calling`

员工端 / 管理端 / AI 助手抽屉 / Agent 运营面板，权限与预算由代码强制，不靠模型自觉

[Get Started](#get-started) · [How It Works](#how-it-works) · [API Reference](#api-reference) · [Agent 设计](hrms-agent/README.md)

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-Vue3%20%C2%B7%20TS%20%C2%B7%20Element%20Plus-42b883)
![Agent](https://img.shields.io/badge/agent-7%20tools%20%C2%B7%203%20planners-orange)
![Tests](https://img.shields.io/badge/unit%20tests-33-brightgreen)

</div>

---

一个人事业务系统（9 张业务表、员工端 + 管理端）加一个跑在它上面的对话 Agent：
用自然语言完成查假期、报考勤、提交请假、主管审批、问制度。
**Agent 只做编排，权限、校验、数据一致性全部留在业务系统**——所有工具都走 HRMS REST，不直连数据库。

## Contents

- [What it does](#what-it-does)
- [Get Started](#get-started)
- [Why this design?](#why-this-design)
- [How It Works](#how-it-works)
- [Key Features](#key-features)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Evaluation](#evaluation)
- [Tests](#tests)
- [Project Layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Data and Disclaimer](#data-and-disclaimer)

## What it does

| 能力 | 在哪 | 说明 |
| --- | --- | --- |
| 🧑‍💼 员工自助 | 员工端（5 个页面） | 打卡 / 请假 / 工资条 / 公告 / 个人档案，只看自己的数据 |
| 🧑‍💻 主管办公 | 管理端（8 个页面） | 员工与组织架构、考勤统计、请假审批、假期类型维护、薪资发放、公告发布 |
| 🤖 事务 Agent | 前端 AI 助手抽屉 | 一句"帮我请下周一到周三的年假"→ 权限校验 → 确认卡片 → 真正提交 |
| 📊 Agent 运营面板 | 管理端「Agent 面板」 | 总量 / 成功率 / 拦截率 / 延迟 / 待确认 / token 六个 KPI、每日趋势、工具 Top、最近调用 |
| 📚 制度问答 | Agent 的 `search_policy` 工具 | 透传用户 JWT 调用[知擎知识库](https://github.com/Lcj666-li/ZhiQing-v1.0)，服务不可用时自动降级 |

**三个模块、三个端口**：

| 模块 | 技术 | 端口 |
| --- | --- | --- |
| `hrms-backend` | FastAPI + SQLAlchemy + MySQL | 8000 |
| `hrms-agent` | FastAPI + Function Calling（OpenAI 兼容） | 8010 |
| `hrms-frontend` | Vue 3 + TypeScript + Element Plus（Vite） | 5173 |

## Get Started

> 建议 Python 3.11+（Agent 镜像基线即 `python:3.11-slim`）、Node 18+、MySQL 8。

### 1. 初始化数据库

```bash
mysql -uroot -p < hrms-backend/sql/init.sql        # 建库 + 9 张表 + 演示账号
# 老库升级：mysql -uroot -p hrms < hrms-backend/sql/migration_add_leave_type_salary.sql
```

`init.sql` 已 seed 两个演示账号（bcrypt 存密码）：`employee / 123456`、`manager / 123456`。

### 2. 起业务后端（8000）

```bash
cd hrms-backend
pip install -r requirements.txt
cp .env.example .env            # 改 DATABASE_URL 的密码，JWT_SECRET_KEY 换成随机长串
python run.py                   # Swagger: http://127.0.0.1:8000/docs
```

### 3. 起 Agent（8010）

```bash
cd hrms-agent
pip install -r requirements.txt
pip install PyMySQL             # store.py 与 seed 脚本要用，requirements.txt 暂未列出
cp .env.example .env            # LLM_API_KEY 留空即走规则模式，0 token 也能全链路跑通
python run.py --selfcheck       # 自检 HRMS 连通性与工具注册，不需要 LLM key
python run.py
```

需要更多演示数据：`python scripts/seed_demo_data.py`。

### 4. 起前端（5173）

```bash
cd hrms-frontend
npm install && npm run dev      # /api 代理到 8000，Agent 地址默认 8010
```

打开 <http://localhost:5173> 用演示账号登录；主管账号登录后能看到「Agent 面板」。

### 5. 跑测试与评测

```bash
cd hrms-agent && pytest                          # 33 个离线用例，不需要 MySQL / HRMS / LLM
cd hrms-agent && python eval/run_eval.py --compare   # 26 条任务，三种 Planner 对比（需后端在跑）
```

## Why this design?

让 LLM 直接办业务的真实风险，和这里各自的对策：

| 风险 | 对策 |
| --- | --- |
| 模型拿到写接口，一句话就能提交/审批 | 编排固定四步 **权限校验 → 人工确认 → 工具执行 → 结果落库**；写操作首轮只返回 `needs_confirmation` 与待执行参数，带 `confirmed=true` 再调才真执行 |
| 只靠提示词约束角色，被话术绕过 | 角色校验做**两层**：Planner 只拿到本角色可见的工具 schema；执行前 `app/guard.py` 再硬校验，越权直接拒绝并写审计 |
| 请求体写 `role: manager` 就能冒充 | 身份**只认 JWT**：角色由 HRMS `/api/auth/me` 解析，无 token → 401，body 里的 role 与 token 不一致 → 403 |
| 余额没查就答"可以休" | 写操作**前置校验**：先查余额（缺数据自动补一次查询，trace 里可见两步），不足直接 `blocked` 并给替代建议，不进确认环节 |
| 用户连点两次 → 两张请假单 | **参数级幂等**：同人 + 同假种 + 同区间已有 pending 就返回原单；审批过的单子再批返回 `idempotent` |
| 全交给大模型，贵、慢、不可复现 | 三种 Planner 并存，默认 Hybrid：规则承接高频意图（**0 token**），LLM 只兜长尾；LLM 调用失败自动降级规则版并计数，主链路不断 |
| 工资明细被原样塞进模型上下文 | `query_my_salary` 只回**脱敏区间**，精确数字留在业务接口 |
| Agent 上线后是黑盒 | 每轮 trace 落**独立库** `hrms_agent`（不碰业务表），管理端面板看 KPI；写 trace 失败只打日志，不影响答题 |
| 外部制度库挂了就报错 | `search_policy` 未配置 / 非 200 / 超时都降级为"制度库当前不可用"，其余工具照常 |
| 改一版不知道有没有退化 | `eval/tasks.jsonl` **26 条**离线任务集（含 4 条越权陷阱），`--compare` 一条命令对比 rule / llm / hybrid |

## How It Works

```
浏览器 ──► Vue3 前端 (5173)   员工端 · 管理端 · AI 助手抽屉
             │  Authorization: Bearer <JWT>    （/api 由 Vite 代理到 8000）
             ├────────────────────────────────────────────► HRMS 业务后端 (8000)
             │                                              9 张表 · SQLAlchemy · JWT
             ▼                                              考勤 请假 薪资 公告 组织 审批
        Agent 服务 (8010, FastAPI)
             │  鉴权：token → /api/auth/me 取真实角色（body 里声明的 role 不算）
             │  限流：每用户 30 次/分钟 → 429 + Retry-After
             ▼
        Planner    Rule / LLM / Hybrid
             │       ↑ 相对月份由 context.py 确定性替换成具体日期，零 token
             ▼
        Orchestrator    编排状态机
             │  权限校验 ──► 人工确认 ──► 工具执行 ──► 结果落库
             │     guard.py     HITL 闸门      policies.py     trace
             │  越权：拒绝并写 audit.jsonl    超预算：4 步 / 20s / 8000 token → 截断并告知
             ▼
        7 个工具（全部走 HRMS REST，不直连数据库）
             ├─ query_my_leave_balance   query_my_attendance   query_my_salary（脱敏区间）
             ├─ submit_leave *           list_pending_approvals             approve_leave *
             └─ search_policy ──HTTP（8s 超时）──► 知擎知识库 (8080) ──不可用→ 降级提示

        * 写操作：首轮只返回 pending_action 与待执行参数，带 confirmed=true 再调才真正落库
```

编排链路上任一步都可中断：`guard` 拦越权、`policies` 拦余额不足、确认闸门停在
`pending_action`、预算闸门（4 步 / 20s / 8000 token）超了就截断并明确告知。
每一步的工具、状态、耗时、参数、结果都写进 `agent_trace_step`。

## Key Features

- 🔐 **JWT 全链路透传**：Agent 不自建账号体系，用用户自己的 token 调业务 API，
  它能看到的范围天然等于该用户能看到的范围
- 🧱 **工具级 RBAC + 审计**：越权尝试写 `traces/audit.jsonl`，不依赖模型自觉
- ✅ **写操作 HITL 确认**：确认卡片展示待执行参数，二次调用才落库
- 🔁 **幂等**：业务参数层面防重（同人 / 假种 / 日期区间），不依赖请求头或缓存
- 🧮 **确定性预处理**：相对时间（"这个月 / 上个月"）由 `app/context.py` 做月份替换，零 token
- 📉 **逐层降级**：LLM 不可用 → 规则 Planner；制度库不可用 → 提示；trace 写库失败 → 只记日志
- 📊 **可观测**：`agent_trace` / `agent_trace_step` 两张表 + 管理端 KPI 面板 + trace 查询接口
- 🐳 **可容器化**：`hrms-agent/Dockerfile` + `docker-compose.yml`（本机 HRMS 走 `host.docker.internal`）

## API Reference

后端 Swagger 在 <http://127.0.0.1:8000/docs>；Agent 明细见 [hrms-agent/README.md](hrms-agent/README.md)。

**hrms-backend（前缀 `/api`）**

| 分组 | 路由 |
| --- | --- |
| 认证 | `POST /api/auth/login` · `GET /api/auth/me` |
| 用户 | `GET` / `PUT /api/user/profile` |
| 考勤 | `POST /api/attendance/check-in` `check-out` · `GET /api/attendance/my` `today` |
| 请假 | `POST /api/leave` · `GET /api/leave/my` · `PUT /api/leave/{id}/cancel` |
| 假期类型 | `GET /api/leave-types` · 主管 CRUD |
| 薪资 | `GET /api/salary/my` · 主管 CRUD + `POST /api/salary/{id}/issue` |
| 公告 | `GET /api/notice`（列表 / 详情）· 主管 CRUD |
| 主管 | `/api/manager/employees` · `/references/*` · `/attendance/stat` · `/leave/pending` `history` `{id}/approve` `reject` |
| 探活 | `GET /api/health`（另有 `/`、`/docs`、`/redoc`） |

**hrms-agent**

| 接口 | 鉴权 | 作用 |
| --- | --- | --- |
| `GET /agent/health` | 否 | HRMS 连通性、LLM 是否配置、限流阈值 |
| `GET /agent/tools` | JWT | 按当前角色返回可用工具（含参数 schema） |
| `POST /agent/chat` | JWT | `{query, confirmed?, session_id?}` → 答案 + 每步 trace + 预算 |
| `GET /agent/stats?days=7` | JWT（仅主管） | 成功率 / 拦截率 / 延迟 / token / 工具 Top |
| `GET /agent/traces` | JWT（仅主管） | 最近调用，可按状态过滤 |
| `GET /agent/traces/{id}` | JWT（仅主管） | 单条明细（优先查库，回落 JSON 文件） |

## Configuration

各模块独立配置，复制对应 `.env.example` 为 `.env`（`.env` 已在 `.gitignore` 中）：

| 模块 | 键 | 默认 | 说明 |
| --- | --- | --- | --- |
| backend | `DATABASE_URL` | `mysql+pymysql://root:…@127.0.0.1:3306/hrms` | 示例里是占位密码，**必须改** |
| backend | `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | 占位串 / HS256 / 1440 | 生产务必换随机长串 |
| backend | `DEBUG` / `BACKEND_CORS_ORIGINS` | `true` / 5173 两个来源 | DEBUG 同时控制 uvicorn 热重载 |
| agent | `HRMS_BASE_URL` | `http://127.0.0.1:8000` | 所有工具经此调业务 API |
| agent | `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | 空 / DeepSeek 兼容端点 / `deepseek-chat` | **key 留空即走规则模式**，可完全离线 |
| agent | `KB_BASE_URL` / `KB_SUBJECT` | `http://127.0.0.1:8080` / 空 | 留空则制度问答工具自动降级 |
| agent | `AGENT_MAX_STEPS` / `AGENT_TIMEOUT` / `AGENT_MAX_TOKENS` | 4 / 20 / 8000 | 单次任务预算闸门 |
| agent | `AGENT_RATE_LIMIT` | 30（次/分钟/用户） | 进程内滑动窗口，超限 429 |
| agent | `AGENT_MYSQL_DSN` | 独立库 `hrms_agent` | trace 落库；示例密码是占位值 |
| frontend | `VITE_PROXY_TARGET` / `VITE_API_BASE_URL` / `VITE_AGENT_BASE_URL` | 8000 / 走代理 / 8010 | 不配就用代码默认值 |

## Evaluation

`hrms-agent/eval/tasks.jsonl` 共 **26 条**离线任务：17 条正常办理、3 条待确认、
2 条余额不足拦截、4 条越权陷阱（员工调主管工具、主管调员工专属工具等）。

```bash
cd hrms-agent
python eval/run_eval.py                    # 默认 planner，需要 HRMS 后端在跑
python eval/run_eval.py --planner rule     # 只看规则模式（0 token 基线）
python eval/run_eval.py --compare          # rule / llm / hybrid 同套任务对比
```

输出成功率、越权处理结果、平均与 P95 延迟、token 消耗、LLM 调用率、降级率。

> 本 README **不预填跑分数字**：结论依赖实际配置的模型与后端状态，报表
> （`compare.json` / `report_*.json`）运行时生成且未入库，请实跑后再引用。

## Tests

```bash
cd hrms-agent && pytest          # 33 个用例，全部离线
```

| 文件 | 用例数 | 覆盖 |
| --- | --- | --- |
| test_auth_api.py | 6 | 接口鉴权、401 / 403、角色伪造拦截 |
| test_tools.py | 6 | 工具注册、参数校验、写操作需确认、幂等 |
| test_orchestrator.py | 5 | 编排四步链路与中断 |
| test_guard.py | 3 | 工具级 RBAC 与越权审计 |
| test_limits.py | 3 | 每用户限流窗口与预算闸门 |
| test_policy.py | 3 | 余额前置校验（充足放行 / 不足拦截 / 非写操作直传） |
| test_planner.py | 3 | 规则解析、日期换算、无法识别时返回空计划 |
| test_context.py | 2 | 相对月份确定性解析 |
| test_render.py | 2 | 审批结果文案与幂等提示渲染 |

33 个用例集中在 Agent 模块，用假客户端 / monkeypatch 替身，**不需要 MySQL、HRMS 与 LLM**。
业务后端与前端目前没有测试用例——这是已知短板，完整清单见
[docs/技术细节.md](docs/技术细节.md) 的「已知短板」一节。

## Project Layout

```
hrms-v1.0/
├─ hrms-backend/
│  ├─ app/
│  │  ├─ main.py            路由装配、CORS、限流、异常处理
│  │  ├─ config.py          .env 读取（DSN / JWT / CORS）
│  │  ├─ database.py        SQLAlchemy 引擎（pool_pre_ping + recycle）
│  │  ├─ core/              deps.py（JWT 依赖与角色） · security.py（bcrypt 与签发）
│  │  ├─ models/            9 张表
│  │  ├─ routers/           auth · attendance · leave · leave_type · salary · notice · manager
│  │  ├─ schemas/           Pydantic 出入参（7 个模块）
│  │  └─ utils/
│  ├─ sql/                  init.sql（建库 + 9 表 + 演示账号） · migration_add_leave_type_salary.sql
│  └─ run.py                8000
├─ hrms-agent/
│  ├─ app/
│  │  ├─ main.py            HTTP 接口与鉴权（8010）
│  │  ├─ planner.py         Rule / LLM / Hybrid 三种 Planner
│  │  ├─ orchestrator.py    编排状态机（权限 → 确认 → 执行 → 落库）
│  │  ├─ guard.py           工具级 RBAC 与越权审计
│  │  ├─ policies.py        写操作前置校验（余额多跳）
│  │  ├─ limits.py          每用户限流
│  │  ├─ context.py         相对月份解析
│  │  ├─ tools/             base.py · hrms.py（6 个）· kb.py（search_policy）
│  │  ├─ store.py           trace 落库与统计
│  │  └─ trace.py           每步执行记录
│  ├─ eval/                 tasks.jsonl（26 条） · run_eval.py
│  ├─ tests/                33 个 pytest 用例
│  ├─ scripts/              seed_demo_data.py · backfill_traces.py
│  └─ Dockerfile · docker-compose.yml · run.py · README.md
└─ hrms-frontend/
   ├─ src/
   │  ├─ views/employee/    Dashboard · Attendance · Leave · Salary · Notice
   │  ├─ views/manager/     Dashboard · Employees · Attendance · LeaveApproval
   │  │                     · LeaveTypes · Salary · Notice · AgentStats
   │  ├─ layouts/           EmployeeLayout.vue · ManagerLayout.vue
   │  ├─ components/        AiAssistant.vue（助手抽屉 + 确认卡片 + trace 展示）
   │  ├─ api/               request.ts（拦截器）· agent.ts · 各业务模块
   │  └─ router/ · store/ · assets/
   └─ vite.config.ts        5173 · /api 代理目标
```

数据库表清单、后端配置与部署细节、已知短板见 [docs/技术细节.md](docs/技术细节.md)。

## Troubleshooting

**登录就 500 / 连不上数据库**
`hrms-backend/.env` 的 `DATABASE_URL` 密码没改，或没跑 `sql/init.sql`。
引擎已开 `pool_pre_ping` + `pool_recycle=3600`，长时间空闲后"连接被服务端断开"已缓解。

**Agent 起来了但 `/agent/health` 显示 HRMS 不可达**
后端没起或 `HRMS_BASE_URL` 指错。Agent 所有工具都经 REST，后端不在等于没工具。

**没配 LLM key 能用吗**
能。`LLM_API_KEY` 留空即走规则 Planner，`python run.py --selfcheck` 与
`python eval/run_eval.py --planner rule` 都能离线跑通，只是长尾问法识别不到。
key 也可用 `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY`，代码按顺序取第一个非空。

**`ModuleNotFoundError: pymysql`（跑 seed 或 trace 落库时）**
Agent 的 `requirements.txt` 目前没列 pymysql，需手动 `pip install PyMySQL`。

**前端提示"连不上 Agent 服务（8010）"**
Agent 未启动，或 `VITE_AGENT_BASE_URL` 指错。401 会被响应拦截器捕获、清 token 并跳回登录页。

**接口返回 429**
触发每用户 30 次/分钟的限流，响应头带 `Retry-After`。评测脚本连续跑时属正常现象。

**答案里没有出现制度库内容**
`KB_BASE_URL` 未配置或知擎服务不在（含 8 秒超时）时，`search_policy` 降级为
"制度库当前不可用"——设计如此，其余工具不受影响。

**端口冲突**
8000 / 8010 / 5173 都是代码里的默认值（CORS 只放行 5173），改端口要同步动
`config.py`、`vite.config.ts` 与 `src/api/agent.ts`。

## Data and Disclaimer

- 库里内容全部是**演示数据**：`init.sql` 的账号、部门、员工与 `scripts/seed_demo_data.py`
  生成的记录不对应任何真实个人或企业，手机号等字段为假数据。
- 演示账号 `employee / 123456`、`manager / 123456` 与 `.env.example` 里的数据库密码都是
  **占位值，生产必须替换**；密码以 bcrypt 存储，`.env` 已在 `.gitignore` 中不会入库。
- 服务默认监听本机、无 HTTPS、无审计日志与找回密码；限流是单实例进程内计数，
  多实例需网关或 Redis。本项目定位是单机可跑通的原型，对外部署请自行加反向代理与访问控制。
- `agent_trace` 表存问题与答案原文，生产环境需自行做脱敏与保留期策略。
- License：本仓库**尚未指定开源协议**，如需对外授权请先补 `LICENSE`。

---

如果这个项目对你有参考价值，欢迎给个 ⭐；提 issue 前请先跑 `cd hrms-agent && pytest`，
并说明卡在 Get Started 的哪一步。
