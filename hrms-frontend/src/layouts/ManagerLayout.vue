<script setup lang="ts">
/**
 * 经理端布局。
 *
 * 与员工布局结构相同，但菜单、主题色和角色标识不同。
 * 经理不在这里维护个人资料，重心放在员工、考勤、审批和公告管理上。
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Bell,
  Calendar,
  DataBoard,
  DocumentChecked,
  Money,
  SwitchButton,
  Tickets,
  User,
  UserFilled,
} from '@element-plus/icons-vue'

import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)

// 页面标题来自当前路由的 meta.title，各子页面不需要重复声明标题。
const pageTitle = computed(() => String(route.meta.title ?? '经理工作台'))

// 小屏自动折叠菜单，提升移动端可用性。
function updateLayout() {
  isCollapse.value = window.innerWidth < 900
}

async function handleCommand(command: string) {
  if (command !== 'logout') {
    return
  }

  try {
    // 退出前二次确认，防止误操作。
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
  // 监听浏览器尺寸变化。
  window.addEventListener('resize', updateLayout)
})

onUnmounted(() => {
  // 页面销毁时清理事件监听器。
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
        <span v-if="!isCollapse" class="brand-text">HRMS 经理端</span>
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="side-menu"
      >
        <el-menu-item index="/manager/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>
        <el-menu-item index="/manager/employees">
          <el-icon><UserFilled /></el-icon>
          <template #title>员工管理</template>
        </el-menu-item>
        <el-menu-item index="/manager/attendance">
          <el-icon><Calendar /></el-icon>
          <template #title>考勤管理</template>
        </el-menu-item>
        <el-menu-item index="/manager/leave">
          <el-icon><DocumentChecked /></el-icon>
          <template #title>请假审批</template>
        </el-menu-item>
        <el-menu-item index="/manager/leave-types">
          <el-icon><Tickets /></el-icon>
          <template #title>请假类型</template>
        </el-menu-item>
        <el-menu-item index="/manager/salary">
          <el-icon><Money /></el-icon>
          <template #title>薪资管理</template>
        </el-menu-item>
        <el-menu-item index="/manager/agent-stats">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>Agent 面板</template>
        </el-menu-item>
        <el-menu-item index="/manager/notice">
          <el-icon><Bell /></el-icon>
          <template #title>公告管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="content-shell">
      <el-header class="topbar">
        <div class="title-block">
          <span class="page-title">{{ pageTitle }}</span>
          <el-tag size="small" effect="plain">经理</el-tag>
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
  background: #0f766e;
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
  color: #0f766e;
  background: #ecfdf5;
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

.title-block {
  display: flex;
  align-items: center;
  gap: 10px;
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
  background: #b45309;
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
}
</style>
