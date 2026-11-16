<script setup lang="ts">
/**
 * 经理请假类型维护页。
 *
 * 请假类型采用停用而不是物理删除的方式，已被历史申请引用的类型仍可正常显示。
 */

import {
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
import { Edit, Plus, Refresh } from '@element-plus/icons-vue'

import {
  createLeaveType,
  getLeaveTypes,
  updateLeaveType,
  type LeaveType,
} from '@/api/leaveType'

const records = ref<LeaveType[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const activeUpdatingId = ref<number | null>(null)

const form = reactive({
  code: '',
  name: '',
  is_paid: true,
  max_days_per_year: null as number | null,
  requires_approval: true,
  is_active: true,
})

const rules: FormRules = {
  code: [
    { required: true, message: '请输入类型代码', trigger: 'blur' },
    {
      pattern: /^[a-z][a-z0-9_]*$/,
      message: '代码须以小写字母开头，只能包含小写字母、数字和下划线',
      trigger: 'blur',
    },
  ],
  name: [
    { required: true, message: '请输入类型名称', trigger: 'blur' },
  ],
}

function resetForm() {
  Object.assign(form, {
    code: '',
    name: '',
    is_paid: true,
    max_days_per_year: null,
    requires_approval: true,
    is_active: true,
  })
}

async function loadData() {
  loading.value = true
  try {
    records.value = await getLeaveTypes()
  } finally {
    loading.value = false
  }
}

async function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEditDialog(row: LeaveType) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, {
    code: row.code,
    name: row.name,
    is_paid: row.is_paid,
    max_days_per_year:
      row.max_days_per_year === null
        ? null
        : Number(row.max_days_per_year),
    requires_approval: row.requires_approval,
    is_active: row.is_active,
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitLeaveType() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  const payload = {
    code: form.code.trim(),
    name: form.name.trim(),
    is_paid: form.is_paid,
    max_days_per_year: form.max_days_per_year,
    requires_approval: form.requires_approval,
    is_active: form.is_active,
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createLeaveType(payload)
      ElMessage.success('请假类型已创建')
    } else if (editingId.value !== null) {
      await updateLeaveType(editingId.value, payload)
      ElMessage.success('请假类型已更新')
    }
    dialogVisible.value = false
    await loadData()
  } finally {
    submitting.value = false
  }
}

async function handleStatusChange(
  row: LeaveType,
  value: string | number | boolean,
) {
  const nextStatus = Boolean(value)

  if (!nextStatus) {
    try {
      await ElMessageBox.confirm(
        `停用“${row.name}”后，员工端将不能再选择该类型，确认继续吗？`,
        '停用请假类型',
        {
          type: 'warning',
          confirmButtonText: '停用',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }
  }

  activeUpdatingId.value = row.id
  try {
    await updateLeaveType(row.id, { is_active: nextStatus })
    ElMessage.success(nextStatus ? '请假类型已启用' : '请假类型已停用')
    await loadData()
  } finally {
    activeUpdatingId.value = null
  }
}

onMounted(loadData)
</script>

<template>
  <section class="panel">
    <div class="toolbar">
      <div>
        <h2>请假类型</h2>
        <span>共 {{ records.length }} 种，停用后不影响历史请假记录</span>
      </div>
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          新增类型
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="records">
      <el-table-column prop="code" label="类型代码" min-width="130" />
      <el-table-column prop="name" label="类型名称" min-width="130" />
      <el-table-column label="薪资待遇" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_paid ? 'success' : 'info'">
            {{ row.is_paid ? '带薪' : '不带薪' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="年度上限" width="120">
        <template #default="{ row }">
          {{
            row.max_days_per_year === null
              ? '不限'
              : `${row.max_days_per_year} 天`
          }}
        </template>
      </el-table-column>
      <el-table-column label="审批要求" width="120">
        <template #default="{ row }">
          {{ row.requires_approval ? '需要审批' : '无需审批' }}
        </template>
      </el-table-column>
      <el-table-column label="启用状态" width="120">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active"
            :loading="activeUpdatingId === row.id"
            inline-prompt
            active-text="启"
            inactive-text="停"
            @change="handleStatusChange(row, $event)"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">
          {{ row.created_at.replace('T', ' ').slice(0, 16) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :icon="Edit"
            @click="openEditDialog(row)"
          >
            编辑
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无请假类型" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增请假类型' : '编辑请假类型'"
      width="620px"
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
            <el-form-item label="类型代码" prop="code">
              <el-input
                v-model="form.code"
                maxlength="30"
                placeholder="例如 annual"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="类型名称" prop="name">
              <el-input
                v-model="form.name"
                maxlength="50"
                placeholder="例如 年假"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="年度最大天数">
              <el-input-number
                v-model="form.max_days_per_year"
                :min="0"
                :precision="1"
                :step="1"
                controls-position="right"
                placeholder="不填表示不限"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="是否带薪">
              <el-switch
                v-model="form.is_paid"
                active-text="带薪"
                inactive-text="不带薪"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="是否需要审批">
              <el-switch
                v-model="form.requires_approval"
                active-text="需要"
                inactive-text="不需要"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="启用状态">
              <el-switch
                v-model="form.is_active"
                active-text="启用"
                inactive-text="停用"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitLeaveType"
        >
          保存
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

.toolbar h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.toolbar span {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
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
