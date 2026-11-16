# HRMS 事务 Agent

在自研 HRMS（FastAPI + MySQL + Vue3，9 张业务表）之上实现的事务办理 Agent：
用自然语言触发 Function Calling 完成假期 / 考勤 / 薪资 / 请假 / 审批 / 制度问答，
写操作必须人工确认，权限与预算由代码强制保证。

## 架构

```
Vue3 前端 / API 调用 → Agent 服务（8010）
    Planner（规则匹配 + LLM 兜底） → Executor（调工具）
    工具层：7 个工具，透传用户 JWT，工具级 RBAC + 写操作人工确认
        ↓ HTTP
    HRMS 业务 API（8000，权限与校验仍在业务系统）
        ↓
    知擎知识库（8080，制度问答，可选，不可用时自动降级）
```

编排链路固定为四步，任一步可中断：

```
权限校验 → 人工确认 → 工具执行 → 结果落库
```

## 工具与权限

| 工具 | 员工 | 主管 | 写操作 | 需确认 |
|---|---|---|---|---|
| query_my_leave_balance | ✅ | ❌ |  |  |
| query_my_attendance | ✅ | ✅ |  |  |
| query_my_salary | ✅ | ✅ |  |  |
| submit_leave | ✅ | ✅ | ✅ | ✅ |
| list_pending_approvals | ❌ | ✅ |  |  |
| approve_leave | ❌ | ✅ | ✅ | ✅ |
| search_policy | ✅ | ✅ |  |  |

角色校验做在两层：

1. **暴露层**：Planner 只拿到当前角色可见的工具 schema（`app/planner.py`）；
2. **执行层**：即使模型选错工具，执行前仍由 `app/guard.py` 按角色硬校验，
   越权直接拒绝并写审计（`traces/audit.jsonl`），不依赖模型自觉。

## 快速开始

```bash
# 1) 安装依赖（建议 Python 3.11+）
pip install -r requirements.txt

# 2) 配置：复制 .env.example 为 .env，按需修改（LLM key 留空也能离线跑规则模式）

# 3) 先起 HRMS 后端（8000，见 ../hrms-backend）

# 4) 自检（不需要 LLM key）
python run.py --selfcheck

# 5) 起 Agent 服务（8010）
python run.py

# 6) 离线评测（需要 HRMS 后端在跑）
python eval/run_eval.py
```

## 接口

| 接口 | 鉴权 | 说明 |
|---|---|---|
| `GET /agent/health` | 否 | HRMS 连通性、LLM 是否配置、限流阈值 |
| `GET /agent/tools` | JWT | 按当前角色返回可用工具（含参数 schema） |
| `POST /agent/chat` | JWT | `{query, confirmed?, session_id?}` → 答案 + 每步 trace + 预算 |
| `GET /agent/stats?days=7` | JWT（仅主管） | 成功率 / 拦截率 / 延迟 / token / 工具 Top |
| `GET /agent/traces` | JWT（仅主管） | 最近调用，可按状态过滤 |
| `GET /agent/traces/{id}` | JWT（仅主管） | 单条明细（优先查库，回落 JSON 文件） |

身份只认 JWT：角色从 HRMS 的 `/api/auth/me` 解析；无 token → 401；
请求体里的 `role` 与 token 不一致 → 403（防角色伪造）。

## 安全与正确性

### 写操作人工确认（HITL）

写操作（submit_leave / approve_leave）第一次调用只返回 `needs_confirmation`
和待执行参数，前端展示确认卡片；用户确认后带 `confirmed=true` 再调一次才真正执行。

### 写操作前置校验（多跳）

`app/policies.py`：提交请假前先查余额（没有余额数据就自动补一次查询，trace 里可见两步），
余额不足直接 `blocked` 并给出替代建议，不进入人工确认环节。

### 参数级幂等

不依赖请求头或缓存，直接在业务参数层面防重：

- `submit_leave`：同人 + 同假种 + 同日期区间已有 pending 记录 → 返回原单，不再 POST；
- `approve_leave`：单子已处理过 → 返回 `idempotent`，不再 PUT。

### 限流与预算

- 每用户 30 次/分钟（进程内滑动窗口，超限 429 + `Retry-After`，`app/limits.py`）；
- 单次任务最多 4 步、20s 总时限、8000 token（`.env` 可调），超预算截断并明确告知。

## Planner：规则承接高频，LLM 兜底长尾

| 实现 | 机制 | 成本 |
|---|---|---|
| RulePlanner | 关键词 + 正则，确定性 | 0 token |
| LLMPlanner | DeepSeek function calling，工具 schema 交给模型自选 | 按次计费 |
| HybridPlanner | 规则命中高置信意图直接走规则，否则交 LLM | 显著低于纯 LLM |

LLM 调用失败（网络 / 鉴权 / 格式）自动降级规则版并计数，主链路不中断。
相对时间（"这个月 / 上个月"）由 `app/context.py` 做确定性月份替换，零 token。

## 评测与测试

- **离线任务集**：`eval/tasks.jsonl` 共 26 条（17 条正常、3 条待确认、2 条余额不足拦截、
  4 条越权陷阱）。越权陷阱覆盖员工调主管工具、主管调员工专属工具等场景，
  全部由 guard 在执行前拦截；
- `python eval/run_eval.py --compare`：rule / llm / hybrid 三种 Planner 跑同一套任务，
  输出成功率、越权处理、延迟、token、降级率对比；
- **单元测试**：`pytest tests/` 共 33 个用例，覆盖工具注册与参数校验、两层 RBAC、
  确认闸门、预算闸门、限流窗口、参数级幂等、前置校验、月份解析、接口鉴权。
  全部离线可跑，不依赖真实 HRMS / LLM / MySQL。

## trace 落库与运营面板

每轮问答写一条 trace 到 MySQL（独立库 `hrms_agent`，不碰 HRMS 业务表）：

| 表 | 内容 |
|---|---|
| `agent_trace` | 会话、问题、角色、状态、planner、intent、token、总耗时、步数 |
| `agent_trace_step` | 每一步的工具、状态、耗时、参数、结果、错误 |

- 历史回填：`python scripts/backfill_traces.py`（重复执行幂等，先清旧步骤再写入）；
- 运营面板：HRMS 前端管理端菜单「Agent 面板」（`/manager/agent-stats`），
  含总量 / 成功率 / 拦截率 / 延迟 / 待确认 / token 六个 KPI、每日趋势、工具 Top、最近调用。

## 部署

```bash
docker compose up -d --build
```

HRMS 跑在本机时用 `host.docker.internal`（compose 已配 `extra_hosts`）；
同在一个 compose 网络里改成服务名即可。

## 目录结构

```
app/
  main.py          HTTP 接口与鉴权
  planner.py       Rule / LLM / Hybrid 三种 Planner
  orchestrator.py  编排状态机（权限 → 确认 → 执行 → 落库）
  guard.py         工具级 RBAC 与越权审计
  policies.py      写操作前置校验（余额多跳）
  limits.py        每用户限流
  context.py       相对月份解析
  tools/           7 个业务工具（全部走 HRMS REST，不直连数据库）
  store.py         trace 落库与统计
  trace.py         每步执行记录
eval/              26 条离线任务集与评测脚本
tests/             33 个 pytest 用例
scripts/           演示数据种子、trace 回填
```

## 已知限制

- 限流是单实例进程内计数，多实例需要网关或 Redis；
- trace 表存问题与答案原文，生产环境需要脱敏与保留期策略；
- 制度问答依赖知擎知识库服务，不可用时降级为"制度库不可用"提示。