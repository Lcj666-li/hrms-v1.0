<script setup lang="ts">
/**
 * 员工端布局。
 *
 * 这个组件只负责所有员工页面共有的部分：
 * 侧栏菜单、顶部标题、用户下拉菜单、个人资料弹窗和退出登录。
 * 真正的业务页面通过 <router-view /> 注入到内容区。
 */

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  ArrowDown,
  Bell,
  Calendar,
  Document,
  HomeFilled,
  Money,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'

import {
  getProfile,
  updateProfile,
  type UserProfile,
} from '@/api/auth'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 小屏幕时侧栏自动折叠，只在布局层保存，不进入 Pinia。
const isCollapse = ref(false)

// 个人资料弹窗的显示状态、加载状态和表单引用。
const profileDialogVisible = ref(false)
const profileLoading = ref(false)
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
const profile = ref<UserProfile | null>(null)
const profileForm = ref({
  name: '',
  gender: '',
  phone: '',
  email: '',
})

// 员工只能修改姓名、性别、手机和邮箱；部门、职位、入职日期由公司维护。
const profileRules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    {
      type: 'email',
      message: '请输入正确的邮箱地址',
      trigger: 'blur',
    },
  ],
}

const pageTitle = computed(() => String(route.meta.title ?? '员工工作台'))

// 监听窗口尺寸，900 像素以下折叠菜单，让页面更适合小屏。
function updateLayout() {
  isCollapse.value = window.innerWidth < 900
}

async function openProfileDialog() {
  profileDialogVisible.value = true
  profileLoading.value = true
  try {
    // 每次打开都重新请求，确保看到的是数据库中的最新资料。
    const data = await getProfile()
    profile.value = data
    profileForm.value = {
      name: data.name,
      gender: data.gender ?? '',
      phone: data.phone ?? '',
      email: data.email ?? '',
    }
    // DOM 更新后再清理上一次的校验提示。
    await nextTick()
    profileFormRef.value?.clearValidate()
  } finally {
    profileLoading.value = false
  }
}

async function submitProfile() {
  // validate() 失败时会 reject，这里转成 false，避免控制台出现未处理异常。
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  profileSubmitting.value = true
  try {
    const updated = await updateProfile({
      // 空字符串统一转成 null，表示“不填写”，避免把空白值写入数据库。
      name: profileForm.value.name.trim(),
      gender: profileForm.value.gender || null,
      phone: profileForm.value.phone.trim() || null,
      email: profileForm.value.email.trim() || null,
    })
    profile.value = updated
    // 姓名可能变化，同步刷新 Pinia，顶部头像和问候语会立即更新。
    await userStore.fetchMe()
    ElMessage.success('个人资料已更新')
    profileDialogVisible.value = false
  } finally {
    profileSubmitting.value = false
  }
}

async function handleCommand(command: string) {
  // el-dropdown 通过 command 区分“个人资料”和“退出登录”。
  if (command === 'profile') {
    await openProfileDialog()
    return
  }

  if (command !== 'logout') {
    return
  }

  try {
    // 退出属于不可逆操作，先让用户确认，避免误点。
    await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
    userStore.logout()
    await router.replace('/login')
  } catch {
    // 用户取消退出时不执行任何操作。
  }
}

onMounted(() => {
  updateLayout()
  // 监听窗口变化，实现响应式侧栏。
  window.addEventListener('resize', updateLayout)
})

onUnmounted(() => {
  // 组件销毁时移除监听，避免内存泄漏。
  window.removeEventListener('resize', updateLayout)
})
</script>

<template>
  <el-container class="app-layout">
    <el-aside
      class="sidebar"
      :width="isCollapse ? '64px' : '220px'"
    >
      <div class="brand" :class="{ compact: isCollapse }">
        <div class="brand-mark">H</div>
        <span v-if="!isCollapse" class="brand-text">HRMS 员工端</span>
      </div>

      <!-- router 模式让每个 menu-item 的 index 直接作为跳转路径。 -->
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="side-menu"
      >
        <el-menu-item index="/employee/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>
        <el-menu-item index="/employee/attendance">
          <el-icon><Calendar /></el-icon>
          <template #title>我的考勤</template>
        </el-menu-item>
        <el-menu-item index="/employee/leave">
          <el-icon><Document /></el-icon>
          <template #title>我的请假</template>
        </el-menu-item>
        <el-menu-item index="/employee/salary">
          <el-icon><Money /></el-icon>
          <template #title>我的工资</template>
        </el-menu-item>
        <el-menu-item index="/employee/notice">
          <el-icon><Bell /></el-icon>
          <template #title>公告</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="content-shell">
      <el-header class="topbar">
        <div class="title-block">
          <span class="page-title">{{ pageTitle }}</span>
        </div>

        <el-dropdown trigger="click" @command="handleCommand">
          <button class="user-trigger" type="button">
            <el-avatar :size="34" class="user-avatar">
              {{ userStore.user?.name?.charAt(0) }}
            </el-avatar>
            <span class="user-name">{{ userStore.user?.name }}</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                <el-icon><User /></el-icon>
                {{ userStore.user?.name }}
              </el-dropdown-item>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人资料
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="page-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog
    v-model="profileDialogVisible"
    title="个人资料"
    width="min(520px, 92vw)"
    destroy-on-close
  >
    <div v-loading="profileLoading">
      <el-descriptions
        v-if="profile"
        :column="2"
        border
        class="profile-summary"
      >
        <el-descriptions-item label="用户名">
          {{ profile.username }}
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">
          <el-tag :type="profile.is_active ? 'success' : 'danger'" size="small">
            {{ profile.is_active ? '正常' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="部门">
          {{ profile.department || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="职位">
          {{ profile.position || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="入职日期" :span="2">
          {{ profile.hire_date || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-position="top"
        class="profile-form"
      >
        <el-form-item label="姓名" prop="name">
          <el-input
            v-model="profileForm.name"
            maxlength="50"
            placeholder="请输入姓名"
          />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select
            v-model="profileForm.gender"
            clearable
            placeholder="请选择性别"
            style="width: 100%"
          >
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="profileForm.phone"
            maxlength="20"
            placeholder="请输入手机号"
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="profileForm.email"
            maxlength="100"
            placeholder="请输入邮箱"
          />
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="profileDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="profileSubmitting"
        @click="submitProfile"
      >
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #f3f6f9;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  background: #ffffff;
  border-right: 1px solid #e7ebf0;
  transition: width 0.2s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 16px;
  border-bottom: 1px solid #edf0f4;
}

.brand.compact {
  justify-content: center;
  padding: 0;
}

.brand-mark {
  display: grid;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  color: #ffffff;
  font-size: 18px;
  font-weight: 700;
  place-items: center;
  background: #2563eb;
  border-radius: 8px;
}

.brand-text {
  overflow: hidden;
  color: #1f2937;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
}

.side-menu {
  border-right: 0;
}

.side-menu :deep(.el-menu-item) {
  height: 48px;
  margin: 4px 8px;
  border-radius: 6px;
}

.side-menu :deep(.el-menu-item.is-active) {
  color: #1d4ed8;
  background: #eef4ff;
}

.content-shell {
  min-width: 0;
}

.topbar {
  display: flex;
  position: sticky;
  z-index: 10;
  top: 0;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e7ebf0;
}

.page-title {
  color: #1f2937;
  font-size: 18px;
  font-weight: 700;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  color: #303133;
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.user-trigger:hover {
  background: #f5f7fa;
}

.user-avatar {
  color: #ffffff;
  background: #0f766e;
}

.user-name {
  max-width: 130px;
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow-icon {
  color: #909399;
}

.page-main {
  padding: 24px;
}

.profile-summary {
  margin-bottom: 20px;
}

.profile-form {
  display: grid;
  gap: 0 14px;
  grid-template-columns: 1fr 1fr;
}

.profile-form :deep(.el-form-item) {
  min-width: 0;
}

@media (max-width: 700px) {
  .topbar {
    padding: 0 14px;
  }

  .user-name {
    display: none;
  }

  .page-main {
    padding: 14px;
  }

  .profile-form {
    grid-template-columns: 1fr;
  }
}
</style>
