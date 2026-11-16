import axios from 'axios'
import type { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

import { TOKEN_STORAGE_KEY } from './request'

/**
 * Agent 服务（默认 8010）的调用封装。
 *
 * 与业务接口分开：Agent 是独立进程，baseURL 可通过 VITE_AGENT_BASE_URL 配置。
 * 身份仍然用 HRMS 的 JWT，Agent 会拿它去 /api/auth/me 换取角色。
 */

export interface AgentStep {
  index: number
  tool: string
  args: Record<string, unknown>
  status: string
  latency_ms: number
  result?: unknown
  error?: string
}

export type AgentStatus = 'ok' | 'needs_confirmation' | 'denied' | 'blocked' | 'failed'

export interface AgentResponse {
  status: AgentStatus
  answer: string
  session_id: string
  role: string
  steps: AgentStep[]
  pending_action?: { tool: string; args: Record<string, unknown> } | null
  verdict?: { intent?: string; note?: string } | null
  total_ms: number
  budget: Record<string, unknown>
}

export interface AgentRequest {
  query: string
  confirmed?: boolean
  session_id?: string
}

const baseURL = import.meta.env.VITE_AGENT_BASE_URL || 'http://127.0.0.1:8010'

const agentHttp = axios.create({ baseURL, timeout: 90000 })

agentHttp.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function describeError(error: AxiosError): string {
  const status = error.response?.status
  const detail = (error.response?.data as { detail?: string } | undefined)?.detail
  if (status === 401) return detail || '未登录或登录已过期，请重新登录'
  if (status === 403) return detail || '当前账号无权执行该操作'
  if (error.code === 'ERR_NETWORK') return '连不上 Agent 服务（8010），请确认它已启动'
  return detail || error.message || '请求失败'
}

export async function askAgent(payload: AgentRequest): Promise<AgentResponse> {
  try {
    const { data } = await agentHttp.post<AgentResponse>('/agent/chat', payload)
    return data
  } catch (error) {
    const message = describeError(error as AxiosError)
    ElMessage.error(message)
    throw new Error(message)
  }
}

export async function fetchAgentHealth(): Promise<{ status: string; hrms: boolean; llm: boolean; tools: number }> {
  const { data } = await agentHttp.get('/agent/health')
  return data
}

export interface AgentStats {
  days: number
  total: number
  ok: number
  success_rate: number
  blocked: number
  denied: number
  needs_confirmation: number
  failed: number
  refused: number
  guard_rate: number
  avg_ms: number
  p95_ms: number
  tokens: number
  avg_steps: number
  by_planner: Array<[string, number]>
  by_day: Array<{ date: string; total: number; ok: number; blocked: number }>
  top_tools: Array<{ tool: string; count: number; avg_ms: number }>
}

export interface AgentTraceRow {
  id: string
  session_id: string | null
  query: string
  role: string
  status: string
  planner: string
  tokens: number
  total_ms: number
  steps: number
  created_at: string
}

export async function fetchAgentStats(days = 7): Promise<AgentStats> {
  const { data } = await agentHttp.get<AgentStats>('/agent/stats', { params: { days } })
  return data
}

export async function fetchAgentTraces(limit = 20, status?: string): Promise<AgentTraceRow[]> {
  const { data } = await agentHttp.get<AgentTraceRow[]>('/agent/traces', { params: { limit, status } })
  return data
}
