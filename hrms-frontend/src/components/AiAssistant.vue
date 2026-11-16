<template>
  <!-- 右下角悬浮入口 + 右侧抽屉 -->
  <button v-if="!visible" class="ai-fab" type="button" title="AI 助手" @click="open()">
    <el-icon><ChatDotRound /></el-icon>
    <span>AI 助手</span>
  </button>

  <el-drawer v-model="visible" direction="rtl" size="460px" :with-header="false" class="ai-drawer">
    <div class="ai-shell">
      <header class="ai-header">
        <div class="ai-title">
          <el-icon><MagicStick /></el-icon>
          <span>AI 事务助手</span>
          <el-tag size="small" :type="health?.llm ? 'success' : 'info'" effect="plain">
            {{ health?.llm ? 'LLM 已连接' : '规则模式' }}
          </el-tag>
        </div>
        <el-icon class="ai-close" @click="visible = false"><Close /></el-icon>
      </header>

      <main ref="listRef" class="ai-messages">
        <div v-if="!messages.length" class="ai-empty">
          <p>可以这样问：</p>
          <div class="ai-chips">
            <el-button v-for="item in examples" :key="item" size="small" round @click="ask(item)">
              {{ item }}
            </el-button>
          </div>
        </div>

        <div v-for="msg in messages" :key="msg.id" :class="['ai-row', msg.role]">
          <div class="ai-bubble">
            <div v-if="msg.role === 'assistant'" class="ai-bubble-head">
              <el-tag size="small" :type="statusTag(msg.response?.status)" effect="light">
                {{ statusText(msg.response?.status, msg) }}
              </el-tag>
              <span v-if="msg.response" class="ai-cost">{{ msg.response.total_ms }} ms</span>
            </div>
            <p class="ai-text">{{ msg.text }}</p>

            <!-- 待确认的写操作 -->
            <div v-if="msg.response?.pending_action" class="ai-confirm">
              <div class="ai-confirm-title">
                需要确认：{{ toolText(msg.response.pending_action.tool) }}
              </div>
              <div class="ai-confirm-args">{{ formatArgs(msg.response.pending_action.args) }}</div>
              <div class="ai-confirm-actions">
                <el-button size="small" type="primary" :loading="loading" @click="confirm(msg)">
                  确认执行
                </el-button>
                <el-button size="small" @click="cancel(msg)">取消</el-button>
              </div>
            </div>

            <!-- 每步工具调用 -->
            <el-collapse v-if="msg.response?.steps?.length" class="ai-steps">
              <el-collapse-item :title="`执行明细（${msg.response.steps.length} 步）`" :name="msg.id">
                <div v-for="step in msg.response.steps" :key="step.index" class="ai-step">
                  <span class="ai-step-index">#{{ step.index }}</span>
                  <span class="ai-step-tool">{{ step.tool }}</span>
                  <el-tag size="small" :type="step.status === 'ok' ? 'success' : 'danger'" effect="plain">
                    {{ step.status }}
                  </el-tag>
                  <span class="ai-step-ms">{{ step.latency_ms }} ms</span>
                  <div v-if="step.error" class="ai-step-error">{{ step.error }}</div>
                  <pre v-if="step.result" class="ai-step-result">{{ pretty(step.result) }}</pre>
                </div>
              </el-collapse-item>
            </el-collapse>

            <!-- 制度问答的引用来源 -->
            <div v-if="sourcesOf(msg).length" class="ai-sources">
              <span class="ai-sources-title">参考来源：</span>
              <span v-for="src in sourcesOf(msg)" :key="src.index" class="ai-source">
                [{{ src.index }}] {{ src.title }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="loading" class="ai-row assistant">
          <div class="ai-bubble ai-thinking">正在规划并调用工具…</div>
        </div>
      </main>

      <footer class="ai-input">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="2"
          resize="none"
          maxlength="200"
          show-word-limit
          placeholder="例如：我还有几天年假？/ 帮我请 12-30 到 12-31 的年假"
          @keydown.enter.exact.prevent="ask()"
        />
        <div class="ai-input-actions">
          <span class="ai-hint">Enter 发送 · Shift+Enter 换行</span>
          <el-button type="primary" :loading="loading" :disabled="!draft.trim()" @click="ask()">
            发送
          </el-button>
        </div>
      </footer>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * AI 助手抽屉：调用 Agent 服务（8010）。
 *
 * 交互要点：
 * 1. 写操作返回 needs_confirmation 时，必须点「确认执行」才会真正提交；
 * 2. 展示每步工具调用与耗时，出问题能看出是规划错还是工具错。
 */
import { nextTick, onMounted, ref } from 'vue'

import { askAgent, fetchAgentHealth } from '@/api/agent'
import type { AgentResponse, AgentStep } from '@/api/agent'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  query?: string
  response?: AgentResponse
}

const SESSION_KEY = 'agent_session_id'

const examples = [
  '我还有几天年假？',
  '这个月工资发了吗？',
  '有哪些待审批的请假？',
  '公司年假制度是怎样的？',
]

const visible = ref(false)
const loading = ref(false)
const draft = ref('')
const messages = ref<ChatMessage[]>([])
const listRef = ref<HTMLElement | null>(null)
const health = ref<{ llm: boolean; hrms: boolean; tools: number } | null>(null)

// 同一次会话复用 session_id，执行记录里可以按会话检索
function sessionId(): string {
  let value = sessionStorage.getItem(SESSION_KEY)
  if (!value) {
    value = uid()
    sessionStorage.setItem(SESSION_KEY, value)
  }
  return value
}

function uid(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function open() {
  visible.value = true
  if (!health.value) {
    try {
      health.value = await fetchAgentHealth()
    } catch {
      health.value = null
    }
  }
  scrollToBottom()
}

function statusText(status?: string, msg?: ChatMessage): string {
  if (msg?.response?.pending_action) return '待确认'
  switch (status) {
    case 'ok':
      return '已完成'
    case 'blocked':
      return '已拦截'
    case 'denied':
      return '无权限'
    case 'failed':
      return '执行失败'
    default:
      return '处理中'
  }
}

function statusTag(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'ok':
      return 'success'
    case 'blocked':
      return 'warning'
    case 'denied':
      return 'danger'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}

function toolText(tool: string): string {
  const map: Record<string, string> = {
    submit_leave: '提交请假申请',
    approve_leave: '审批请假',
    query_my_leave_balance: '查询假期余额',
    query_my_attendance: '查询考勤',
    query_my_salary: '查询薪资',
    list_pending_approvals: '查询待审批',
    search_policy: '查询制度',
  }
  return map[tool] || tool
}

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(' · ')
}

function pretty(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function sourcesOf(msg: ChatMessage): Array<{ index: number; title: string }> {
  const steps: AgentStep[] = msg.response?.steps || []
  for (const step of steps) {
    const result = step.result as { sources?: Array<{ index: number; title: string }> } | undefined
    if (result?.sources?.length) return result.sources
  }
  return []
}

async function send(query: string, confirmed: boolean, baseId?: string) {
  if (!query.trim() || loading.value) return
  loading.value = true
  const id = baseId || uid()
  try {
    const response = await askAgent({ query, confirmed, session_id: sessionId() })
    messages.value.push({
      id: `${id}-reply-${messages.value.length}`,
      role: 'assistant',
      text: response.answer || '（无内容）',
      query,
      response,
    })
  } catch (error) {
    messages.value.push({
      id: `${id}-error-${messages.value.length}`,
      role: 'assistant',
      text: (error as Error).message,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function ask(text?: string) {
  const query = (text ?? draft.value).trim()
  if (!query) return
  draft.value = ''
  messages.value.push({ id: uid(), role: 'user', text: query })
  scrollToBottom()
  await send(query, false)
}

async function confirm(msg: ChatMessage) {
  if (!msg.query) return
  await send(msg.query, true)
}

function cancel(msg: ChatMessage) {
  if (msg.response) msg.response.pending_action = null
  messages.value.push({
    id: uid(),
    role: 'assistant',
    text: '已取消，本次没有写入任何数据。',
  })
  scrollToBottom()
}

onMounted(() => {
  // 有登录态时预取一次健康状态，用于显示"LLM 是否连接"
  if (localStorage.getItem('hrms_token')) {
    fetchAgentHealth()
      .then((data) => {
        health.value = data
      })
      .catch(() => {
        health.value = null
      })
  }
})
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 28px;
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 999px;
  background: #409eff;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.35);
}

.ai-fab:hover {
  background: #337ecc;
}

.ai-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f7f9fc;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.ai-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
}

.ai-close {
  cursor: pointer;
  color: #909399;
}

.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.ai-empty {
  color: #909399;
  font-size: 13px;
}

.ai-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.ai-row {
  display: flex;
  margin-bottom: 12px;
}

.ai-row.user {
  justify-content: flex-end;
}

.ai-bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  font-size: 13px;
  line-height: 1.6;
}

.ai-row.user .ai-bubble {
  background: #409eff;
  color: #fff;
}

.ai-bubble-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ai-cost {
  color: #909399;
  font-size: 12px;
}

.ai-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-thinking {
  color: #909399;
  font-style: italic;
}

.ai-confirm {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
}

.ai-confirm-title {
  font-weight: 600;
  color: #b88230;
  font-size: 13px;
}

.ai-confirm-args {
  margin: 4px 0 8px;
  color: #606266;
  font-size: 12px;
  word-break: break-all;
}

.ai-confirm-actions {
  display: flex;
  gap: 8px;
}

.ai-steps {
  margin-top: 10px;
  border-top: 1px dashed #ebeef5;
  --el-collapse-header-font-size: 12px;
}

.ai-step {
  padding: 6px 0;
  border-bottom: 1px dashed #f2f3f5;
  font-size: 12px;
}

.ai-step-index {
  color: #909399;
  margin-right: 6px;
}

.ai-step-tool {
  font-weight: 600;
  margin-right: 8px;
}

.ai-step-ms {
  color: #909399;
  margin-left: 8px;
}

.ai-step-error {
  color: #f56c6c;
  margin-top: 4px;
}

.ai-step-result {
  margin: 6px 0 0;
  padding: 6px 8px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 11px;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.ai-sources {
  margin-top: 10px;
  font-size: 12px;
  color: #606266;
}

.ai-sources-title {
  font-weight: 600;
}

.ai-source {
  margin-right: 8px;
}

.ai-input {
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #ebeef5;
}

.ai-input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.ai-hint {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
