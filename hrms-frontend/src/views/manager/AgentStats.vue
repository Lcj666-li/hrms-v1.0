<template>
  <div class="agent-stats">
    <div class="page-head">
      <div>
        <h2>Agent 运营面板</h2>
        <p class="sub">近 {{ days }} 天的调用量、成功率、拦截情况与工具耗时（数据来自 agent_trace 表）</p>
      </div>
      <div class="head-actions">
        <el-radio-group v-model="days" size="small" @change="load">
          <el-radio-button :value="1">今天</el-radio-button>
          <el-radio-button :value="7">近 7 天</el-radio-button>
          <el-radio-button :value="30">近 30 天</el-radio-button>
        </el-radio-group>
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />

    <div class="kpi-grid">
      <div class="kpi">
        <span class="kpi-label">总请求</span>
        <span class="kpi-value">{{ stats?.total ?? 0 }}</span>
        <span class="kpi-sub">平均 {{ stats?.avg_steps ?? 0 }} 步/次</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">成功率</span>
        <span class="kpi-value">{{ percent(stats?.success_rate) }}</span>
        <span class="kpi-sub">已完成 {{ stats?.ok ?? 0 }} 条</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">拦截率</span>
        <span class="kpi-value">{{ percent(stats?.guard_rate) }}</span>
        <span class="kpi-sub">阻断 {{ stats?.blocked ?? 0 }} · 越权 {{ stats?.denied ?? 0 }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">平均耗时</span>
        <span class="kpi-value">{{ stats?.avg_ms ?? 0 }} ms</span>
        <span class="kpi-sub">P95 {{ stats?.p95_ms ?? 0 }} ms</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">待确认</span>
        <span class="kpi-value">{{ stats?.needs_confirmation ?? 0 }}</span>
        <span class="kpi-sub">写操作人工确认</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">Token 消耗</span>
        <span class="kpi-value">{{ formatNumber(stats?.tokens) }}</span>
        <span class="kpi-sub">近 {{ days }} 天累计</span>
      </div>
    </div>

    <div class="panel-grid">
      <el-card shadow="never" class="panel">
        <template #header><span class="panel-title">每日调用量</span></template>
        <div v-if="!stats?.by_day?.length" class="empty">暂无数据</div>
        <div v-else class="bars">
          <div v-for="day in stats.by_day" :key="day.date" class="bar-row">
            <span class="bar-date">{{ day.date.slice(5) }}</span>
            <div class="bar-track">
              <div class="bar-ok" :style="{ width: ratio(day.ok, maxDay) }"></div>
              <div class="bar-blocked" :style="{ width: ratio(day.blocked, maxDay) }"></div>
            </div>
            <span class="bar-value">{{ day.total }}</span>
          </div>
          <div class="legend">
            <span><i class="dot ok"></i>完成</span>
            <span><i class="dot blocked"></i>拦截/越权</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="panel">
        <template #header><span class="panel-title">工具调用 Top</span></template>
        <el-table :data="stats?.top_tools ?? []" size="small" :show-header="true">
          <el-table-column prop="tool" label="工具" />
          <el-table-column prop="count" label="次数" width="80" align="right" />
          <el-table-column prop="avg_ms" label="平均耗时(ms)" width="120" align="right" />
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never" class="panel">
      <template #header><span class="panel-title">最近调用</span></template>
      <el-table :data="traces" size="small">
        <el-table-column prop="query" label="问题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="role" label="角色" width="90" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="planner" label="Planner" width="120" />
        <el-table-column prop="steps" label="步数" width="70" align="right" />
        <el-table-column prop="total_ms" label="耗时(ms)" width="100" align="right" />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchAgentStats, fetchAgentTraces } from '@/api/agent'
import type { AgentStats, AgentTraceRow } from '@/api/agent'

const days = ref(7)
const loading = ref(false)
const error = ref('')
const stats = ref<AgentStats | null>(null)
const traces = ref<AgentTraceRow[]>([])

const maxDay = computed(() =>
  Math.max(1, ...(stats.value?.by_day ?? []).map((d) => d.total)),
)

function percent(value?: number): string {
  return `${Math.round((value ?? 0) * 100)}%`
}

function formatNumber(value?: number): string {
  if (!value) return '0'
  return value >= 10000 ? `${(value / 1000).toFixed(1)}k` : String(value)
}

function ratio(value: number, max: number): string {
  return `${Math.min(100, Math.round((value / max) * 100))}%`
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'ok') return 'success'
  if (status === 'blocked') return 'warning'
  if (status === 'denied' || status === 'failed') return 'danger'
  return 'info'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, t] = await Promise.all([fetchAgentStats(days.value), fetchAgentTraces(20)])
    stats.value = s
    traces.value = t
  } catch (err) {
    error.value = `加载失败：${(err as Error).message}（请确认 Agent 服务 8010 已启动）`
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.agent-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-head h2 {
  margin: 0;
  font-size: 20px;
}
.sub {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.kpi {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.kpi-label {
  color: #909399;
  font-size: 12px;
}
.kpi-value {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}
.kpi-sub {
  color: #c0c4cc;
  font-size: 12px;
}
.panel-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 16px;
}
@media (max-width: 1100px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}
.panel-title {
  font-weight: 600;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.bar-date {
  width: 48px;
  color: #909399;
}
.bar-track {
  flex: 1;
  display: flex;
  height: 14px;
  background: #f5f7fa;
  border-radius: 7px;
  overflow: hidden;
}
.bar-ok {
  background: #67c23a;
}
.bar-blocked {
  background: #e6a23c;
}
.bar-value {
  width: 40px;
  text-align: right;
  color: #606266;
}
.legend {
  display: flex;
  gap: 16px;
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 4px;
  border-radius: 50%;
}
.dot.ok {
  background: #67c23a;
}
.dot.blocked {
  background: #e6a23c;
}
.empty {
  color: #909399;
  font-size: 13px;
}
</style>
