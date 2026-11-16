<script setup lang="ts">
/**
 * 经理员工管理页。
 *
 * 支持员工列表、关键词/部门筛选、新增、编辑、启用/禁用和重置密码。
 * 新增和编辑共用一套表单，通过 dialogMode 区分字段和校验规则。
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
import { Edit, Key, Plus, Refresh, Search } from '@element-plus/icons-vue'

import {
  createEmployee,
  getEmployees,
  toggleEmployeeStatus,
  updateEmployee,
  type EmployeeCreatePayload,
  type EmployeeUpdatePayload,
  type UserProfile,
} from '@/api/auth'

const employees = ref<UserProfile[]>([])
const loading = ref(false)
// 前端筛选条件：keyword 同时匹配姓名、用户名、部门和职位。
const keyword = ref('')
const departmentFilter = ref('')

const dialogVisible = ref(false)
// create 表示新增，edit 表示编辑；editingId 仅编辑时有值。
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)

const passwordDialogVisible = ref(false)
const passwordTarget = ref<UserProfile | null>(null)
const passwordFormRef = ref<FormInstance>()
const passwordSubmitting = ref(false)

const form = reactive({
  username: '',
  password: '',
  name: '',
  gender: '',
  phone: '',
  email: '',
  department: '',
  position: '',
  hire_date: '',
  is_active: true,
})

const passwordForm = reactive({
  password: '',
})

// 密码规则根据弹窗模式动态变化：新增必须填写，编辑时密码由单独弹窗处理。
const rules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 位', trigger: 'blur' },
  ],
  password:
    dialogMode.value === 'create'
      ? [
          { required: true, message: '请输入初始密码', trigger: 'blur' },
          {
            min: 6,
            max: 128,
            message: '密码长度为 6-128 位',
            trigger: 'blur',
          },
        ]
      : [],
  name: [
    { required: true, message: '请输入员工姓名', trigger: 'blur' },
  ],
}))

const passwordRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    {
      min: 6,
      max: 128,
      message: '密码长度为 6-128 位',
      trigger: 'blur',
    },
  ],
}

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '新增员工' : '编辑员工',
)

const departments = computed(() =>
  // 从员工数据中去重并排序，得到部门筛选下拉框的选项。
  Array.from(
    new Set(
      employees.value
        .map((employee) => employee.department)
        .filter((department): department is string => Boolean(department)),
    ),
  ).sort(),
)

const filteredEmployees = computed(() => {
  // 所有筛选都在前端完成，适合当前毕业设计的数据规模。
  const value = keyword.value.trim().toLowerCase()
  return employees.value.filter((employee) => {
    const matchesKeyword =
      !value ||
      [
        employee.name,
        employee.username,
        employee.department,
        employee.position,
      ].some((field) => field?.toLowerCase().includes(value))
    const matchesDepartment =
      !departmentFilter.value ||
      employee.department === departmentFilter.value
    return matchesKeyword && matchesDepartment
  })
})

function textOrNull(value: string) {
  // 空字符串转换为 null，让可选字段在数据库中保持为空而不是空串。
  return value.trim() ? value.trim() : null
}

function formatDate(value?: string | null) {
  return value || '-'
}

async function loadEmployees() {
  loading.value = true
  try {
    employees.value = await getEmployees()
  } finally {
    loading.value = false
  }
}

function resetForm() {
  // 使用 Object.assign 重置字段，保持 reactive 对象引用不变。
  Object.assign(form, {
    username: '',
    password: '',
    name: '',
    gender: '',
    phone: '',
    email: '',
    department: '',
    position: '',
    hire_date: '',
    is_active: true,
  })
}

async function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
  // 等弹窗渲染完成后再清理校验状态。
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEditDialog(row: UserProfile) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    name: row.name,
    gender: row.gender ?? '',
    phone: row.phone ?? '',
    email: row.email ?? '',
    department: row.department ?? '',
    position: row.position ?? '',
    hire_date: row.hire_date ?? '',
    is_active: row.is_active,
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitEmployee() {
  // 根据当前模式组装不同请求体，避免页面上维护两套几乎相同的表单。
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      // 新增员工必须包含用户名和初始密码。
      const payload: EmployeeCreatePayload = {
        username: form.username.trim(),
        password: form.password,
        name: form.name.trim(),
        gender: textOrNull(form.gender),
        phone: textOrNull(form.phone),
        email: textOrNull(form.email),
        department: textOrNull(form.department),
        position: textOrNull(form.position),
        hire_date: form.hire_date || null,
        is_active: form.is_active,
      }
      await createEmployee(payload)
      ElMessage.success('员工账号已创建')
    } else if (editingId.value !== null) {
      // 编辑不传 password，密码重置由独立接口处理。
      const payload: EmployeeUpdatePayload = {
        username: form.username.trim(),
        name: form.name.trim(),
        gender: textOrNull(form.gender),
        phone: textOrNull(form.phone),
        email: textOrNull(form.email),
        department: textOrNull(form.department),
        position: textOrNull(form.position),
        hire_date: form.hire_date || null,
        is_active: form.is_active,
      }
      await updateEmployee(editingId.value, payload)
      ElMessage.success('员工资料已更新')
    }

    dialogVisible.value = false
    await loadEmployees()
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: UserProfile) {
  // 同一个接口负责启用和禁用，按钮文案根据当前状态推导。
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定${action}员工“${row.name}”的账号吗？`,
      `${action}账号`,
      {
        type: 'warning',
        confirmButtonText: action,
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  const result = await toggleEmployeeStatus(row.id)
  ElMessage.success(result.message)
  await loadEmployees()
}

async function openPasswordDialog(row: UserProfile) {
  passwordTarget.value = row
  passwordForm.password = ''
  passwordDialogVisible.value = true
  await nextTick()
  passwordFormRef.value?.clearValidate()
}

async function submitPasswordReset() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid || passwordTarget.value === null) {
    return
  }

  passwordSubmitting.value = true
  try {
    // 复用员工更新接口，只提交 password 字段，后端会识别并重新生成 bcrypt 哈希。
    await updateEmployee(passwordTarget.value.id, {
      password: passwordForm.password,
    })
    ElMessage.success('密码已重置')
    passwordDialogVisible.value = false
  } finally {
    passwordSubmitting.value = false
  }
}

onMounted(loadEmployees)
</script>

<template>
  <section class="panel">
    <div class="toolbar">
      <div class="filter-grid">
        <el-input
          v-model="keyword"
          :prefix-icon="Search"
          clearable
          placeholder="姓名、用户名、部门或职位"
        />
        <el-select
          v-model="departmentFilter"
          clearable
          placeholder="全部部门"
        >
          <el-option
            v-for="department in departments"
            :key="department"
            :label="department"
            :value="department"
          />
        </el-select>
      </div>
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadEmployees">刷新</el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          新增员工
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="filteredEmployees" height="560">
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="name" label="姓名" width="110" />
      <el-table-column prop="department" label="部门" width="130">
        <template #default="{ row }">
          {{ row.department || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="position" label="职位" width="140">
        <template #default="{ row }">
          {{ row.position || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="140">
        <template #default="{ row }">
          {{ row.phone || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="入职日期" width="120">
        <template #default="{ row }">
          {{ formatDate(row.hire_date) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active"
            inline-prompt
            active-text="启"
            inactive-text="禁"
            @change="toggleStatus(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :icon="Edit"
            @click="openEditDialog(row)"
          >
            编辑
          </el-button>
          <el-button
            type="warning"
            link
            :icon="Key"
            @click="openPasswordDialog(row)"
          >
            重置密码
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="没有符合条件的员工" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="720px"
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
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>
          <el-col v-if="dialogMode === 'create'" :xs="24" :sm="12">
            <el-form-item label="初始密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="至少 6 位"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="form.name" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="性别">
              <el-select
                v-model="form.gender"
                clearable
                placeholder="请选择"
                style="width: 100%"
              >
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="部门">
              <el-input v-model="form.department" placeholder="请输入部门" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="职位">
              <el-input v-model="form.position" placeholder="请输入职位" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="入职日期">
              <el-date-picker
                v-model="form.hire_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择入职日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="账号状态">
              <el-switch
                v-model="form.is_active"
                active-text="启用"
                inactive-text="禁用"
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
          @click="submitEmployee"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="passwordDialogVisible"
      title="重置密码"
      width="420px"
      destroy-on-close
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
      >
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="passwordForm.password"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="passwordSubmitting"
          @click="submitPasswordReset"
        >
          确认重置
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
  grid-template-columns: minmax(220px, 340px) 180px;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 760px) {
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
</style>
