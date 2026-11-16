<script setup lang="ts">
/**
 * 经理考勤管理页。
 *
 * 上层显示月度统计，下层显示全员考勤明细。
 * 明细支持日期、部门和姓名三个条件组合筛选。
 */

import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'

import { getEmployees } from '@/api/auth'
import {
  getAllAttendance,
  getAttendanceStat,
  type AttendanceRecord,
  type AttendanceStat,
  type AttendanceStatus,
} from '@/api/attendance'

const now = new Date()
const month = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
)
const filters = reactive({
  // 空字符串代表未选择，提交前统一转换为 undefined。
  date: '',
  department: '',
  name: '',
})
const records = ref<AttendanceRecord[]>([])
const stat = ref<AttendanceStat | null>(null)
const departments = ref<string[]>([])
const loading = ref(false)

const statusText: Record<AttendanceStatus, string> = {
  normal: '正常',
  late: '迟到',
  early: '早退',
  late_early: '迟到且早退',
  missing: '缺卡',
  absent: '缺勤',
}

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

const statItems = computed(() => [
  // 把统计对象转换成模板可直接循环的数组，颜色与业务含义对应。
  { label: '正常', value: stat.value?.normal ?? 0, color: '#15803d' },
  { label: '迟到', value: stat.value?.late ?? 0, color: '#c2410c' },
  { label: '早退', value: stat.value?.early ?? 0, color: '#b45309' },
  {
    label: '迟到且早退',
    value: stat.value?.late_early ?? 0,
    color: '#b91c1c',
  },
  { label: '缺卡', value: stat.value?.missing ?? 0, color: '#64748b' },
  { label: '缺勤', value: stat.value?.absent ?? 0, color: '#991b1b' },
])

function formatTime(value?: string | null) {
  return value ? value.slice(0, 8) : '--:--'
}

async function loadAttendance() {
  loading.value = true
  try {
    // 空筛选值不发送给后端，后端会按“不限制该条件”处理。
    records.value = await getAllAttendance({
      date: filters.date || undefined,
      department: filters.department || undefined,
      name: filters.name.trim() || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function loadStat() {
  stat.value = await getAttendanceStat(month.value)
}

async function loadDepartments() {
  const employees = await getEmployees()
  // Set 去重，filter 排除空部门，sort 让下拉选项顺序稳定。
  departments.value = Array.from(
    new Set(
      employees
        .map((employee) => employee.department)
        .filter((department): department is string => Boolean(department)),
    ),
  ).sort()
}

function resetFilters() {
  filters.date = ''
  filters.department = ''
  filters.name = ''
  // 清空条件后立即重新查询。
  loadAttendance()
}

onMounted(async () => {
  loading.value = true
  try {
    // 明细、统计、部门选项三个请求互不依赖，并行执行。
    await Promise.all([loadAttendance(), loadStat(), loadDepartments()])
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-stack">
    <section class="panel stat-panel">
      <div class="panel-heading">
        <div>
          <h2>月度考勤统计</h2>
          <span>出勤率 {{ stat?.attendance_rate ?? 0 }}%</span>
        </div>
        <el-date-picker
          v-model="month"
          type="month"
          value-format="YYYY-MM"
          :clearable="false"
          @change="loadStat"
        />
      </div>

      <div class="stat-grid">
        <div
          v-for="item in statItems"
          :key="item.label"
          class="stat-item"
        >
          <span class="stat-dot" :style="{ background: item.color }" />
          <div>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <div class="filter-grid">
          <el-date-picker
            v-model="filters.date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            clearable
          />
          <el-select
            v-model="filters.department"
            clearable
            placeholder="选择部门"
          >
            <el-option
              v-for="department in departments"
              :key="department"
              :label="department"
              :value="department"
            />
          </el-select>
          <el-input
            v-model="filters.name"
            clearable
            placeholder="员工姓名"
            @keyup.enter="loadAttendance"
          />
        </div>
        <div class="toolbar-actions">
          <el-button :icon="Search" type="primary" @click="loadAttendance">
            查询
          </el-button>
          <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="records" height="510">
        <el-table-column prop="date" label="日期" width="116" />
        <el-table-column prop="user_name" label="姓名" width="110" />
        <el-table-column prop="department" label="部门" width="130">
          <template #default="{ row }">
            {{ row.department || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="上班" width="105">
          <template #default="{ row }">
            {{ formatTime(row.check_in) }}
          </template>
        </el-table-column>
        <el-table-column label="下班" width="105">
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
          min-width="160"
          show-overflow-tooltip
        />
        <template #empty>
          <el-empty description="没有符合条件的考勤记录" />
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

.panel {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.panel-heading h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.panel-heading span {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.stat-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 76px;
  padding: 14px;
  background: #f8fafc;
  border-radius: 6px;
}

.stat-dot {
  width: 8px;
  height: 40px;
  border-radius: 4px;
}

.stat-item span {
  color: #64748b;
  font-size: 12px;
}

.stat-item strong {
  display: block;
  margin-top: 5px;
  color: #172033;
  font-size: 22px;
  line-height: 1;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.filter-grid {
  display: grid;
  flex: 1;
  gap: 10px;
  grid-template-columns: 180px 170px minmax(180px, 260px);
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 1050px) {
  .stat-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .panel-heading,
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }
}
</style>
