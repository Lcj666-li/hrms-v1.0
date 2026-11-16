<script setup lang="ts">
/**
 * 经理工作台。
 *
 * 聚合展示全局关键指标：员工数量、启用账号、待审批请假和本月出勤率。
 * 页面本身不执行业务修改，只负责把多个统计接口汇总为管理概览。
 */

import { computed, onMounted, ref } from 'vue'
import {
  Calendar,
  DocumentChecked,
  TrendCharts,
  UserFilled,
} from '@element-plus/icons-vue'

import { getEmployees } from '@/api/auth'
import {
  getAttendanceStat,
  type AttendanceStat,
} from '@/api/attendance'
import {
  getPendingLeaves,
  type LeaveRecord,
} from '@/api/leave'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
// employees、pendingLeaves 和 attendanceStat 分别对应三个独立统计接口。
const employees = ref<Awaited<ReturnType<typeof getEmployees>>>([])
const pendingLeaves = ref<LeaveRecord[]>([])
const attendanceStat = ref<AttendanceStat | null>(null)

const now = new Date()
const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const todayText = now.toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long',
})

const activeEmployeeCount = computed(
  // 只有 is_active = true 的账号才计入“启用账号”。
  () => employees.value.filter((employee) => employee.is_active).length,
)
const recentLeaves = computed(() => pendingLeaves.value.slice(0, 5))

function formatDateTime(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

async function loadDashboard() {
  loading.value = true
  try {
    // 三个请求互不依赖，并行加载可以缩短工作台首屏等待时间。
    const [employeeList, leaveList, stat] = await Promise.all([
      getEmployees(),
      getPendingLeaves(),
      getAttendanceStat(currentMonth),
    ])
    employees.value = employeeList
    pendingLeaves.value = leaveList
    attendanceStat.value = stat
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page-stack" v-loading="loading">
    <section class="welcome-band">
      <div>
        <span class="welcome-label">经理工作台</span>
        <h2>{{ userStore.user?.name }}</h2>
        <p>{{ todayText }}</p>
      </div>
      <div class="period">
        <el-icon><Calendar /></el-icon>
        <span>{{ currentMonth }}</span>
      </div>
    </section>

    <div class="metric-grid">
      <div class="metric-item">
        <div class="metric-icon blue">
          <el-icon><UserFilled /></el-icon>
        </div>
        <div>
          <span>员工总数</span>
          <strong>{{ employees.length }}</strong>
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-icon green">
          <el-icon><UserFilled /></el-icon>
        </div>
        <div>
          <span>启用账号</span>
          <strong>{{ activeEmployeeCount }}</strong>
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-icon orange">
          <el-icon><DocumentChecked /></el-icon>
        </div>
        <div>
          <span>待审批请假</span>
          <strong>{{ pendingLeaves.length }}</strong>
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-icon teal">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div>
          <span>本月出勤率</span>
          <strong>{{ attendanceStat?.attendance_rate ?? 0 }}%</strong>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <section class="panel">
        <div class="panel-heading">
          <h3>待审批请假</h3>
          <span>最近 5 条</span>
        </div>
        <el-table :data="recentLeaves" height="300">
          <el-table-column prop="user_name" label="员工" width="110" />
          <el-table-column prop="department" label="部门" width="120">
            <template #default="{ row }">
              {{ row.department || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="请假日期" min-width="180">
            <template #default="{ row }">
              {{ row.start_date }} 至 {{ row.end_date }}
            </template>
          </el-table-column>
          <el-table-column label="申请时间" width="150">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无待审批申请" />
          </template>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <h3>本月考勤分布</h3>
          <span>{{ currentMonth }}</span>
        </div>

        <div class="distribution-list">
          <div class="distribution-row">
            <span>正常</span>
            <strong>{{ attendanceStat?.normal ?? 0 }}</strong>
          </div>
          <div class="distribution-row">
            <span>迟到</span>
            <strong>{{ attendanceStat?.late ?? 0 }}</strong>
          </div>
          <div class="distribution-row">
            <span>早退</span>
            <strong>{{ attendanceStat?.early ?? 0 }}</strong>
          </div>
          <div class="distribution-row">
            <span>迟到且早退</span>
            <strong>{{ attendanceStat?.late_early ?? 0 }}</strong>
          </div>
          <div class="distribution-row">
            <span>缺卡</span>
            <strong>{{ attendanceStat?.missing ?? 0 }}</strong>
          </div>
          <div class="distribution-row">
            <span>缺勤</span>
            <strong>{{ attendanceStat?.absent ?? 0 }}</strong>
          </div>
        </div>
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
  border-left: 5px solid #0f766e;
  border-radius: 8px;
}

.welcome-label {
  color: #64748b;
  font-size: 14px;
}

.welcome-band h2 {
  margin: 8px 0 6px;
  color: #172033;
  font-size: 28px;
}

.welcome-band p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.period {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0f766e;
  font-size: 20px;
  font-weight: 700;
}

.metric-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 15px;
  min-height: 112px;
  padding: 18px 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
}

.metric-icon {
  display: grid;
  flex: 0 0 auto;
  width: 44px;
  height: 44px;
  color: #ffffff;
  font-size: 20px;
  border-radius: 8px;
  place-items: center;
}

.metric-icon.blue {
  background: #2563eb;
}

.metric-icon.green {
  background: #15803d;
}

.metric-icon.orange {
  background: #c2410c;
}

.metric-icon.teal {
  background: #0f766e;
}

.metric-item span {
  color: #64748b;
  font-size: 13px;
}

.metric-item strong {
  display: block;
  margin-top: 6px;
  color: #172033;
  font-size: 28px;
  line-height: 1;
}

.content-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
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
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 18px;
}

.panel-heading h3 {
  margin: 0;
  color: #172033;
  font-size: 16px;
}

.panel-heading span {
  color: #94a3b8;
  font-size: 12px;
}

.distribution-list {
  display: flex;
  flex-direction: column;
}

.distribution-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 46px;
  color: #64748b;
  border-bottom: 1px solid #edf0f4;
}

.distribution-row:last-child {
  border-bottom: 0;
}

.distribution-row strong {
  color: #172033;
  font-size: 18px;
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

  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
