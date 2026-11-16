<script setup lang="ts">
/**
 * 员工工作台。
 *
 * 页面同时承担三个职责：
 * 1. 展示实时日期、问候语和今日打卡状态；
 * 2. 汇总本月考勤各状态数量；
 * 3. 提供上下班打卡入口和最近 5 条记录。
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Check,
  Clock,
  Refresh,
  Timer,
} from '@element-plus/icons-vue'

import {
  checkIn,
  checkOut,
  getMyAttendance,
  getTodayAttendance,
  type AttendanceRecord,
  type AttendanceStatus,
} from '@/api/attendance'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
// punchAction 用于判断正在执行哪一次打卡，避免两个按钮同时转圈。
const punchAction = ref<'in' | 'out' | ''>('')
const todayRecord = ref<AttendanceRecord | null>(null)
const monthRecords = ref<AttendanceRecord[]>([])
// now 每秒更新一次，驱动页面时钟和问候语自动变化。
const now = ref(new Date())
let timer: number | undefined

// 当前月份格式化成后端要求的 YYYY-MM。
const currentMonth = computed(() => {
  const value = new Date()
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`
})

const greeting = computed(() => {
  const hour = now.value.getHours()
  if (hour < 12) return '上午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const dateText = computed(() =>
  now.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }),
)

const timeText = computed(() =>
  now.value.toLocaleTimeString('zh-CN', {
    hour12: false,
  }),
)

const stats = computed(() => {
  const result: Record<AttendanceStatus, number> = {
    normal: 0,
    late: 0,
    early: 0,
    late_early: 0,
    missing: 0,
    absent: 0,
  }
  for (const record of monthRecords.value) {
    // 每个状态先初始化为 0，避免某状态没有记录时表格显示 undefined。
    result[record.status] += 1
  }
  return result
})

const recentRecords = computed(() => monthRecords.value.slice(0, 5))
const canCheckIn = computed(() => !todayRecord.value?.check_in)
// 必须已经上班打卡，并且还没有下班打卡，才允许下班打卡。
const canCheckOut = computed(
  () => Boolean(todayRecord.value?.check_in) && !todayRecord.value?.check_out,
)

const statusText: Record<AttendanceStatus, string> = {
  normal: '正常',
  late: '迟到',
  early: '早退',
  late_early: '迟到且早退',
  missing: '缺卡',
  absent: '缺勤',
}

// Element Plus 标签类型与业务状态统一映射，页面模板只负责取值。
const statusType: Record<
  AttendanceStatus,
  'success' | 'warning' | 'danger' | 'info'
> = {
  normal: 'success',
  late: 'warning',
  early: 'warning',
  late_early: 'danger',
  missing: 'info',
  absent: 'danger',
}

function formatTime(value?: string | null) {
  return value ? value.slice(0, 8) : '--:--'
}

async function loadData() {
  loading.value = true
  try {
    // 两个接口互不依赖，使用 Promise.all 并行请求以减少等待时间。
    const [today, records] = await Promise.all([
      getTodayAttendance(),
      getMyAttendance(currentMonth.value),
    ])
    todayRecord.value = today
    monthRecords.value = records
  } finally {
    loading.value = false
  }
}

async function handleCheckIn() {
  punchAction.value = 'in'
  try {
    const result = await checkIn()
    ElMessage.success(result.message)
    // 打卡成功后重新拉取数据，让时间和按钮状态立即同步。
    await loadData()
  } finally {
    punchAction.value = ''
  }
}

async function handleCheckOut() {
  punchAction.value = 'out'
  try {
    const result = await checkOut()
    ElMessage.success(result.message)
    await loadData()
  } finally {
    punchAction.value = ''
  }
}

onMounted(() => {
  loadData()
  // 启动秒级时钟。
  timer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  // 页面销毁时必须清除定时器，否则会持续占用资源。
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <div class="page-stack" v-loading="loading">
    <section class="welcome-band">
      <div class="welcome-copy">
        <span class="welcome-label">{{ greeting }}</span>
        <h2>{{ userStore.user?.name }}</h2>
        <p>{{ dateText }}</p>
      </div>
      <div class="clock-block">
        <el-icon><Clock /></el-icon>
        <span>{{ timeText }}</span>
      </div>
    </section>

    <div class="metric-grid">
      <div class="metric-item">
        <span class="metric-label">正常</span>
        <strong>{{ stats.normal }}</strong>
        <span class="metric-unit">天</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">迟到 / 早退</span>
        <strong>{{ stats.late + stats.early }}</strong>
        <span class="metric-unit">天</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">迟到且早退</span>
        <strong>{{ stats.late_early }}</strong>
        <span class="metric-unit">天</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">缺卡</span>
        <strong>{{ stats.missing }}</strong>
        <span class="metric-unit">天</span>
      </div>
    </div>

    <div class="content-grid">
      <section class="panel punch-panel">
        <div class="panel-heading">
          <div>
            <h3>今日打卡</h3>
            <span>{{ currentMonth }} 月度记录</span>
          </div>
          <el-button
            text
            :icon="Refresh"
            @click="loadData"
          >
            刷新
          </el-button>
        </div>

        <div class="punch-times">
          <div class="time-item">
            <span>上班</span>
            <strong>{{ formatTime(todayRecord?.check_in) }}</strong>
          </div>
          <div class="time-divider" />
          <div class="time-item">
            <span>下班</span>
            <strong>{{ formatTime(todayRecord?.check_out) }}</strong>
          </div>
        </div>

        <div class="punch-actions">
          <el-button
            type="primary"
            size="large"
            :icon="Check"
            :disabled="!canCheckIn"
            :loading="punchAction === 'in'"
            @click="handleCheckIn"
          >
            上班打卡
          </el-button>
          <el-button
            type="success"
            size="large"
            :icon="Timer"
            :disabled="!canCheckOut"
            :loading="punchAction === 'out'"
            @click="handleCheckOut"
          >
            下班打卡
          </el-button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <div>
            <h3>最近考勤</h3>
            <span>最近 5 条记录</span>
          </div>
        </div>

        <el-table :data="recentRecords" height="278">
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column label="上班" width="90">
            <template #default="{ row }">
              {{ formatTime(row.check_in) }}
            </template>
          </el-table-column>
          <el-table-column label="下班" width="90">
            <template #default="{ row }">
              {{ formatTime(row.check_out) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="statusType[row.status as AttendanceStatus]"
              >
                {{ statusText[row.status as AttendanceStatus] }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.welcome-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 136px;
  padding: 26px 30px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-left: 5px solid #2563eb;
  border-radius: 8px;
}

.welcome-label {
  color: #64748b;
  font-size: 14px;
}

.welcome-copy h2 {
  margin: 8px 0 6px;
  color: #172033;
  font-size: 28px;
}

.welcome-copy p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.clock-block {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1d4ed8;
  font-size: 30px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.metric-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-item {
  display: grid;
  min-height: 112px;
  padding: 18px 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
  grid-template-columns: 1fr auto;
}

.metric-label {
  color: #64748b;
  font-size: 14px;
  grid-column: 1 / -1;
}

.metric-item strong {
  align-self: end;
  color: #172033;
  font-size: 30px;
  line-height: 1;
}

.metric-unit {
  align-self: end;
  color: #94a3b8;
  font-size: 13px;
}

.content-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
}

.panel {
  min-width: 0;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.panel-heading h3 {
  margin: 0;
  color: #172033;
  font-size: 16px;
}

.panel-heading span {
  display: block;
  margin-top: 5px;
  color: #94a3b8;
  font-size: 12px;
}

.punch-times {
  display: grid;
  align-items: center;
  margin-bottom: 24px;
  grid-template-columns: 1fr 1px 1fr;
}

.time-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: center;
}

.time-item span {
  color: #64748b;
  font-size: 13px;
}

.time-item strong {
  color: #172033;
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.time-divider {
  width: 1px;
  height: 54px;
  background: #e5eaf0;
}

.punch-actions {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 1fr;
}

@media (max-width: 1050px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .welcome-band {
    align-items: flex-start;
    flex-direction: column;
    gap: 18px;
    padding: 22px;
  }

  .clock-block {
    font-size: 24px;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .punch-actions {
    grid-template-columns: 1fr;
  }
}
</style>
