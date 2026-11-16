<script setup lang="ts">
/**
 * 员工工资页。
 *
 * 员工只能看到经理已经确认发放的工资记录，可按月份查询并查看工资组成。
 */

import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { getMySalaries, type SalaryRecord } from '@/api/salary'

const now = new Date()
const month = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
)
const records = ref<SalaryRecord[]>([])
const loading = ref(false)

const totalActual = computed(() =>
  records.value.reduce(
    (total, record) => total + Number(record.actual_salary),
    0,
  ),
)

function formatMoney(value: number) {
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatDateTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

async function loadData() {
  loading.value = true
  try {
    records.value = await getMySalaries(month.value || undefined)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-stack">
    <section class="salary-summary">
      <div class="summary-item">
        <span>查询月份</span>
        <strong>{{ month || '全部月份' }}</strong>
      </div>
      <div class="summary-item">
        <span>工资单数量</span>
        <strong>{{ records.length }}</strong>
      </div>
      <div class="summary-item highlight">
        <span>实发合计</span>
        <strong>¥ {{ formatMoney(totalActual) }}</strong>
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
            clearable
            @change="loadData"
          />
        </div>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="records">
        <el-table-column prop="salary_month" label="工资月份" width="110" />
        <el-table-column label="基本工资" min-width="120" align="right">
          <template #default="{ row }">
            ¥ {{ formatMoney(row.base_salary) }}
          </template>
        </el-table-column>
        <el-table-column label="奖金" min-width="110" align="right">
          <template #default="{ row }">
            ¥ {{ formatMoney(row.bonus) }}
          </template>
        </el-table-column>
        <el-table-column
          label="考勤扣款"
          min-width="120"
          align="right"
        >
          <template #default="{ row }">
            ¥ {{ formatMoney(row.attendance_deduction) }}
          </template>
        </el-table-column>
        <el-table-column
          label="请假扣款"
          min-width="120"
          align="right"
        >
          <template #default="{ row }">
            ¥ {{ formatMoney(row.leave_deduction) }}
          </template>
        </el-table-column>
        <el-table-column label="社保" min-width="110" align="right">
          <template #default="{ row }">
            ¥ {{ formatMoney(row.social_security) }}
          </template>
        </el-table-column>
        <el-table-column label="个税" min-width="110" align="right">
          <template #default="{ row }">
            ¥ {{ formatMoney(row.tax) }}
          </template>
        </el-table-column>
        <el-table-column label="实发工资" min-width="140" align="right">
          <template #default="{ row }">
            <strong class="actual-salary">
              ¥ {{ formatMoney(row.actual_salary) }}
            </strong>
          </template>
        </el-table-column>
        <el-table-column label="发放时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.issued_at) }}
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="当前月份暂无可查看的工资记录" />
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

.salary-summary {
  display: grid;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-left: 5px solid #0f766e;
  border-radius: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-item {
  display: flex;
  min-height: 104px;
  padding: 20px 24px;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  border-right: 1px solid #edf1f5;
}

.summary-item:last-child {
  border-right: 0;
}

.summary-item span {
  color: #64748b;
  font-size: 13px;
}

.summary-item strong {
  color: #172033;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.summary-item.highlight strong {
  color: #0f766e;
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

.actual-salary {
  color: #0f766e;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 760px) {
  .salary-summary {
    grid-template-columns: 1fr;
  }

  .summary-item {
    min-height: 86px;
    border-right: 0;
    border-bottom: 1px solid #edf1f5;
  }

  .summary-item:last-child {
    border-bottom: 0;
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
