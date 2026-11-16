<script setup lang="ts">
/**
 * 员工考勤明细页。
 *
 * 工作台负责概览，本页负责完整记录：支持上下班打卡、
 * 按月份筛选本人考勤，并用标签展示每条记录的状态。
 */

import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Check,
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

const now = new Date()
// 默认查询当前月，value-format 与后端 month 参数保持一致。
const month = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
)
const records = ref<AttendanceRecord[]>([])
const todayRecord = ref<AttendanceRecord | null>(null)
const loading = ref(false)
const actionLoading = ref<'in' | 'out' | ''>('')

const statusText: Record<AttendanceStatus, string> = {
  normal: '正常',
  late: '迟到',
  early: '早退',
  late_early: '迟到且早退',
  missing: '缺卡',
  absent: '缺勤',
}

// 状态到 Element Plus 标签颜色的映射，集中维护，避免模板中出现重复判断。
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
    // 今日状态决定按钮是否可用，月度列表用于下方表格，两者并行请求。
    const [today, list] = await Promise.all([
      getTodayAttendance(),
      getMyAttendance(month.value),
    ])
    todayRecord.value = today
    records.value = list
  } finally {
    loading.value = false
  }
}

async function handleCheckIn() {
  actionLoading.value = 'in'
  try {
    const result = await checkIn()
    ElMessage.success(result.message)
    // 打卡后刷新今日和当前月份的记录。
    await loadData()
  } finally {
    actionLoading.value = ''
  }
}

async function handleCheckOut() {
  actionLoading.value = 'out'
  try {
    const result = await checkOut()
    ElMessage.success(result.message)
    await loadData()
  } finally {
    actionLoading.value = ''
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-stack">
    <section class="punch-bar">
      <div class="punch-summary">
        <div class="summary-item">
          <span>上班打卡</span>
          <strong>{{ formatTime(todayRecord?.check_in) }}</strong>
        </div>
        <div class="summary-divider" />
        <div class="summary-item">
          <span>下班打卡</span>
          <strong>{{ formatTime(todayRecord?.check_out) }}</strong>
        </div>
      </div>

      <div class="punch-actions">
        <el-button
          type="primary"
          :icon="Check"
          :disabled="Boolean(todayRecord?.check_in)"
          :loading="actionLoading === 'in'"
          @click="handleCheckIn"
        >
          上班打卡
        </el-button>
        <el-button
          type="success"
          :icon="Timer"
          :disabled="!todayRecord?.check_in || Boolean(todayRecord?.check_out)"
          :loading="actionLoading === 'out'"
          @click="handleCheckOut"
        >
          下班打卡
        </el-button>
      </div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <div class="filter-group">
          <span class="filter-label">月份</span>
          <el-date-picker
            v-model="month"
            type="month"
            value-format="YYYY-MM"
            placeholder="选择月份"
            :clearable="false"
            @change="loadData"
          />
        </div>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="records">
        <el-table-column prop="date" label="日期" width="130" />
        <el-table-column label="上班打卡" width="130">
          <template #default="{ row }">
            {{ formatTime(row.check_in) }}
          </template>
        </el-table-column>
        <el-table-column label="下班打卡" width="130">
          <template #default="{ row }">
            {{ formatTime(row.check_out) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="statusType[row.status as AttendanceStatus]"
            >
              {{ statusText[row.status as AttendanceStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="remark"
          label="备注"
          min-width="180"
          show-overflow-tooltip
        />
        <template #empty>
          <el-empty description="当前月份暂无考勤记录" />
        </template>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.page-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.punch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 118px;
  padding: 22px 26px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-left: 5px solid #0f766e;
  border-radius: 8px;
}

.punch-summary {
  display: grid;
  align-items: center;
  min-width: 420px;
  grid-template-columns: 1fr 1px 1fr;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.summary-item span {
  color: #64748b;
  font-size: 13px;
}

.summary-item strong {
  color: #172033;
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.summary-divider {
  width: 1px;
  height: 48px;
  margin-right: 42px;
  background: #e5eaf0;
}

.punch-actions {
  display: flex;
  gap: 10px;
}

.panel {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  color: #64748b;
  font-size: 14px;
}

@media (max-width: 760px) {
  .punch-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 20px;
  }

  .punch-summary {
    width: 100%;
    min-width: 0;
  }

  .summary-divider {
    margin-right: 18px;
  }

  .punch-actions {
    width: 100%;
  }

  .punch-actions :deep(.el-button) {
    flex: 1;
  }

  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-group {
    justify-content: space-between;
  }
}
</style>
