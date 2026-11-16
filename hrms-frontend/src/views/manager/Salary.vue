<script setup lang="ts">
/**
 * 经理薪资管理页。
 *
 * 支持按月、员工和状态筛选，新建/编辑薪资草稿，以及确认发放工资。
 * 实发工资始终由后端计算，页面中的金额仅用于提交前预览。
 */

import {
  computed,
  nextTick,
  onMounted,
  reactive,
  ref,
} from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  Check,
  Edit,
  Plus,
  Refresh,
} from '@element-plus/icons-vue'

import { getEmployees, type UserProfile } from '@/api/auth'
import {
  createSalaryRecord,
  getSalaryRecords,
  issueSalaryRecord,
  updateSalaryRecord,
  type SalaryRecord,
  type SalaryStatus,
} from '@/api/salary'

const records = ref<SalaryRecord[]>([])
const employees = ref<UserProfile[]>([])
const loading = ref(false)
const filterMonth = ref('')
const filterEmployee = ref<number | undefined>()
const filterStatus = ref<SalaryStatus | undefined>()

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const issuingId = ref<number | null>(null)

const form = reactive({
  user_id: null as number | null,
  salary_month: '',
  base_salary: 0 as number | null,
  attendance_deduction: 0 as number | null,
  leave_deduction: 0 as number | null,
  bonus: 0 as number | null,
  social_security: 0 as number | null,
  tax: 0 as number | null,
})

const rules: FormRules = {
  user_id: [
    { required: true, message: '请选择员工', trigger: 'change' },
  ],
  salary_month: [
    { required: true, message: '请选择工资月份', trigger: 'change' },
  ],
  base_salary: [
    { required: true, message: '请输入基本工资', trigger: 'blur' },
  ],
}

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '新增薪资记录' : '编辑薪资记录',
)

const previewActualSalary = computed(() => {
  return (
    Number(form.base_salary ?? 0) +
    Number(form.bonus ?? 0) -
    Number(form.attendance_deduction ?? 0) -
    Number(form.leave_deduction ?? 0) -
    Number(form.social_security ?? 0) -
    Number(form.tax ?? 0)
  )
})

function currentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function formatMoney(value: number) {
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatDateTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

function resetForm() {
  Object.assign(form, {
    user_id: null,
    salary_month: currentMonth(),
    base_salary: 0,
    attendance_deduction: 0,
    leave_deduction: 0,
    bonus: 0,
    social_security: 0,
    tax: 0,
  })
}

async function loadData() {
  loading.value = true
  try {
    records.value = await getSalaryRecords({
      month: filterMonth.value || undefined,
      user_id: filterEmployee.value || undefined,
      status: filterStatus.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  employees.value = await getEmployees()
}

async function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEditDialog(row: SalaryRecord) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, {
    user_id: row.user_id,
    salary_month: row.salary_month,
    base_salary: Number(row.base_salary),
    attendance_deduction: Number(row.attendance_deduction),
    leave_deduction: Number(row.leave_deduction),
    bonus: Number(row.bonus),
    social_security: Number(row.social_security),
    tax: Number(row.tax),
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitSalary() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (
    !valid ||
    form.user_id === null ||
    !form.salary_month
  ) {
    return
  }

  const payload = {
    user_id: form.user_id,
    salary_month: form.salary_month,
    base_salary: Number(form.base_salary ?? 0),
    attendance_deduction: Number(form.attendance_deduction ?? 0),
    leave_deduction: Number(form.leave_deduction ?? 0),
    bonus: Number(form.bonus ?? 0),
    social_security: Number(form.social_security ?? 0),
    tax: Number(form.tax ?? 0),
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createSalaryRecord(payload)
      ElMessage.success('薪资草稿已创建')
    } else if (editingId.value !== null) {
      await updateSalaryRecord(editingId.value, payload)
      ElMessage.success('薪资草稿已更新')
    }
    dialogVisible.value = false
    await loadData()
  } finally {
    submitting.value = false
  }
}

async function issueSalary(row: SalaryRecord) {
  try {
    await ElMessageBox.confirm(
      `确认向“${row.user_name || '该员工'}”发放 ${row.salary_month} 的工资吗？发放后不能修改。`,
      '发放工资',
      {
        type: 'warning',
        confirmButtonText: '确认发放',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  issuingId.value = row.id
  try {
    await issueSalaryRecord(row.id)
    ElMessage.success('工资已发放')
    await loadData()
  } finally {
    issuingId.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadEmployees(), loadData()])
})
</script>

<template>
  <section class="panel">
    <div class="toolbar">
      <div class="filter-grid">
        <el-date-picker
          v-model="filterMonth"
          type="month"
          value-format="YYYY-MM"
          placeholder="全部月份"
          clearable
          @change="loadData"
        />
        <el-select
          v-model="filterEmployee"
          clearable
          filterable
          placeholder="全部员工"
          @change="loadData"
        >
          <el-option
            v-for="employee in employees"
            :key="employee.id"
            :label="
              employee.department
                ? `${employee.name}（${employee.department}）`
                : employee.name
            "
            :value="employee.id"
          />
        </el-select>
        <el-select
          v-model="filterStatus"
          clearable
          placeholder="全部状态"
          @change="loadData"
        >
          <el-option label="草稿" value="draft" />
          <el-option label="已发放" value="issued" />
        </el-select>
      </div>
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          新增薪资
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="records" height="560">
      <el-table-column prop="user_name" label="员工" width="110" fixed="left" />
      <el-table-column prop="department" label="部门" width="130">
        <template #default="{ row }">
          {{ row.department || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="salary_month" label="月份" width="100" />
      <el-table-column label="基本工资" min-width="115" align="right">
        <template #default="{ row }">
          ¥ {{ formatMoney(row.base_salary) }}
        </template>
      </el-table-column>
      <el-table-column label="奖金" min-width="105" align="right">
        <template #default="{ row }">
          ¥ {{ formatMoney(row.bonus) }}
        </template>
      </el-table-column>
      <el-table-column
        label="考勤扣款"
        min-width="115"
        align="right"
      >
        <template #default="{ row }">
          ¥ {{ formatMoney(row.attendance_deduction) }}
        </template>
      </el-table-column>
      <el-table-column
        label="请假扣款"
        min-width="115"
        align="right"
      >
        <template #default="{ row }">
          ¥ {{ formatMoney(row.leave_deduction) }}
        </template>
      </el-table-column>
      <el-table-column label="社保" min-width="105" align="right">
        <template #default="{ row }">
          ¥ {{ formatMoney(row.social_security) }}
        </template>
      </el-table-column>
      <el-table-column label="个税" min-width="105" align="right">
        <template #default="{ row }">
          ¥ {{ formatMoney(row.tax) }}
        </template>
      </el-table-column>
      <el-table-column label="实发工资" min-width="130" align="right">
        <template #default="{ row }">
          <strong class="actual-salary">
            ¥ {{ formatMoney(row.actual_salary) }}
          </strong>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.status === 'issued' ? 'success' : 'warning'"
          >
            {{ row.status === 'issued' ? '已发放' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发放时间" width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.issued_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'draft'">
            <el-button
              type="primary"
              link
              :icon="Edit"
              @click="openEditDialog(row)"
            >
              编辑
            </el-button>
            <el-button
              type="success"
              link
              :icon="Check"
              :loading="issuingId === row.id"
              @click="issueSalary(row)"
            >
              发放
            </el-button>
          </template>
          <span v-else class="muted">已完成</span>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="没有符合条件的薪资记录" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="760px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="员工" prop="user_id">
              <el-select
                v-model="form.user_id"
                filterable
                placeholder="请选择员工"
                style="width: 100%"
              >
                <el-option
                  v-for="employee in employees"
                  :key="employee.id"
                  :label="
                    employee.department
                      ? `${employee.name}（${employee.department}）`
                      : employee.name
                  "
                  :value="employee.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="工资月份" prop="salary_month">
              <el-date-picker
                v-model="form.salary_month"
                type="month"
                value-format="YYYY-MM"
                placeholder="选择月份"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="基本工资" prop="base_salary">
              <el-input-number
                v-model="form.base_salary"
                :min="0"
                :precision="2"
                :step="100"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="奖金">
              <el-input-number
                v-model="form.bonus"
                :min="0"
                :precision="2"
                :step="100"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="考勤扣款">
              <el-input-number
                v-model="form.attendance_deduction"
                :min="0"
                :precision="2"
                :step="50"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="请假扣款">
              <el-input-number
                v-model="form.leave_deduction"
                :min="0"
                :precision="2"
                :step="50"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="社保">
              <el-input-number
                v-model="form.social_security"
                :min="0"
                :precision="2"
                :step="50"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="个人所得税">
              <el-input-number
                v-model="form.tax"
                :min="0"
                :precision="2"
                :step="50"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div
          class="salary-preview"
          :class="{ invalid: previewActualSalary < 0 }"
        >
          <span>预计实发工资</span>
          <strong>¥ {{ formatMoney(previewActualSalary) }}</strong>
          <small>
            {{
              previewActualSalary < 0
                ? '扣款和税费合计不能超过基本工资与奖金之和'
                : '最终金额以后端计算结果为准'
            }}
          </small>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="previewActualSalary < 0"
          @click="submitSalary"
        >
          保存草稿
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
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

.filter-grid {
  display: grid;
  flex: 1;
  gap: 10px;
  grid-template-columns: 170px minmax(190px, 260px) 140px;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.actual-salary {
  color: #0f766e;
  font-variant-numeric: tabular-nums;
}

.muted {
  color: #94a3b8;
  font-size: 13px;
}

.salary-preview {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-top: 4px;
  padding: 15px 18px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 6px;
}

.salary-preview span {
  color: #475569;
  font-size: 14px;
}

.salary-preview strong {
  color: #0f766e;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.salary-preview small {
  margin-left: auto;
  color: #64748b;
}

.salary-preview.invalid {
  background: #fef2f2;
  border-color: #fecaca;
}

.salary-preview.invalid strong,
.salary-preview.invalid small {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 600px) {
  .salary-preview {
    align-items: flex-start;
    flex-direction: column;
  }

  .salary-preview small {
    margin-left: 0;
  }
}
</style>
