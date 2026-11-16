<script setup lang="ts">
/**
 * 员工请假页。
 *
 * 页面负责展示本人的请假记录、提交新的请假申请，
 * 以及撤销仍处于 pending 状态的申请。
 */

import { nextTick, onMounted, ref } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import {
  cancelLeave,
  createLeave,
  getMyLeaves,
  type LeaveRecord,
  type LeaveStatus,
} from '@/api/leave'
import {
  getActiveLeaveTypes,
  type LeaveType,
} from '@/api/leaveType'

const records = ref<LeaveRecord[]>([])
const leaveTypes = ref<LeaveType[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  leaveTypeId: null as number | null,
  dateRange: null as [string, string] | null,
  reason: '',
})

// 日期范围组件返回 [开始日期, 结束日期]，自定义校验器检查是否完整选择。
const rules: FormRules = {
  leaveTypeId: [
    { required: true, message: '请选择请假类型', trigger: 'change' },
  ],
  dateRange: [
    {
      required: true,
      validator: (_rule, value, callback) => {
        if (!value || value.length !== 2) {
          callback(new Error('请选择请假日期范围'))
          return
        }
        callback()
      },
      trigger: 'change',
    },
  ],
  reason: [
    { required: true, message: '请输入请假原因', trigger: 'blur' },
  ],
}

const statusText: Record<LeaveStatus, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  cancelled: '已撤销',
}

// 请假状态到标签颜色的统一映射。
const statusType: Record<
  LeaveStatus,
  'success' | 'warning' | 'danger' | 'info'
> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  cancelled: 'info',
}

function formatDateTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

async function loadData() {
  loading.value = true
  try {
    records.value = await getMyLeaves()
  } finally {
    loading.value = false
  }
}

async function loadLeaveTypes() {
  leaveTypes.value = await getActiveLeaveTypes()
}

async function openDialog() {
  // 每次打开都清空上一次的内容，避免误提交旧数据。
  form.value = {
    leaveTypeId: null,
    dateRange: null,
    reason: '',
  }
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitLeave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (
    !valid ||
    form.value.leaveTypeId === null ||
    !form.value.dateRange
  ) {
    return
  }

  submitting.value = true
  try {
    // 把日期范围拆成后端需要的 start_date 和 end_date。
    await createLeave({
      leave_type_id: form.value.leaveTypeId,
      start_date: form.value.dateRange[0],
      end_date: form.value.dateRange[1],
      reason: form.value.reason.trim(),
    })
    ElMessage.success('请假申请已提交')
    dialogVisible.value = false
    await loadData()
  } finally {
    submitting.value = false
  }
}

async function handleCancel(row: LeaveRecord) {
  try {
    await ElMessageBox.confirm(
      '确定撤销这条请假申请吗？',
      '撤销申请',
      {
        type: 'warning',
        confirmButtonText: '撤销',
        cancelButtonText: '返回',
      },
    )
  } catch {
    // 用户点击取消时不执行任何操作。
    return
  }

  const result = await cancelLeave(row.id)
  ElMessage.success(result.message)
  await loadData()
}

onMounted(async () => {
  await Promise.all([loadData(), loadLeaveTypes()])
})
</script>

<template>
  <section class="panel">
    <div class="toolbar">
      <div class="toolbar-title">
        <h2>请假记录</h2>
        <span>共 {{ records.length }} 条</span>
      </div>
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog">
          申请请假
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="records">
      <el-table-column label="请假日期" min-width="210">
        <template #default="{ row }">
          {{ row.start_date }} 至 {{ row.end_date }}
        </template>
      </el-table-column>
      <el-table-column label="请假类型" width="120">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.leave_type_is_paid ? 'success' : 'info'"
            effect="plain"
          >
            {{ row.leave_type_name || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="reason"
        label="请假原因"
        min-width="240"
        show-overflow-tooltip
      />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="statusType[row.status as LeaveStatus]"
          >
            {{ statusText[row.status as LeaveStatus] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审批意见" min-width="180">
        <template #default="{ row }">
          {{ row.approve_comment || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="申请时间" width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            type="danger"
            link
            @click="handleCancel(row)"
          >
            撤销
          </el-button>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无请假记录" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      title="申请请假"
      width="560px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="请假类型" prop="leaveTypeId">
          <el-select
            v-model="form.leaveTypeId"
            placeholder="请选择请假类型"
            style="width: 100%"
          >
            <el-option
              v-for="leaveType in leaveTypes"
              :key="leaveType.id"
              :label="
                leaveType.is_paid
                  ? leaveType.name
                  : `${leaveType.name}（不带薪）`
              "
              :value="leaveType.id"
            >
              <span>{{ leaveType.name }}</span>
              <span class="option-note">
                {{
                  leaveType.max_days_per_year === null
                    ? '天数不限'
                    : `每年 ${leaveType.max_days_per_year} 天`
                }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="请假日期" prop="dateRange">
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="请假原因" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="请输入请假原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitLeave"
        >
          提交申请
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

.toolbar-title h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.toolbar-title span {
  display: block;
  margin-top: 5px;
  color: #94a3b8;
  font-size: 12px;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.muted {
  color: #c0c4cc;
}

.option-note {
  float: right;
  margin-left: 18px;
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 700px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }
}
</style>
