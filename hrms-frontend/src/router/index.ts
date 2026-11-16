import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useUserStore } from '@/store/user'

/**
 * 路由与权限守卫。
 *
 * 前端路由分成三个区域：
 * - /login：公开页面；
 * - /employee/*：员工页面；
 * - /manager/*：经理页面。
 *
 * meta.requiresAuth 控制是否登录，meta.role 控制角色。
 * 真正的数据权限仍由后端接口校验，前端守卫用于避免错误页面和改善体验。
 */

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/employee',
    component: () => import('@/layouts/EmployeeLayout.vue'),
    // 父路由统一声明员工权限，所有子页面自动继承该要求。
    meta: { requiresAuth: true, role: 'employee' },
    children: [
      {
        path: '',
        redirect: '/employee/dashboard',
      },
      {
        path: 'dashboard',
        name: 'employee-dashboard',
        component: () => import('@/views/employee/Dashboard.vue'),
        meta: { title: '员工工作台' },
      },
      {
        path: 'attendance',
        name: 'employee-attendance',
        component: () => import('@/views/employee/Attendance.vue'),
        meta: { title: '我的考勤' },
      },
      {
        path: 'salary',
        name: 'employee-salary',
        component: () => import('@/views/employee/Salary.vue'),
        meta: { title: '我的工资' },
      },
      {
        path: 'leave',
        name: 'employee-leave',
        component: () => import('@/views/employee/Leave.vue'),
        meta: { title: '我的请假' },
      },
      {
        path: 'agent-stats',
        name: 'manager-agent-stats',
        component: () => import('@/views/manager/AgentStats.vue'),
        meta: { title: 'Agent 运营面板' },
      },
      {
        path: 'notice',
        name: 'employee-notice',
        component: () => import('@/views/employee/Notice.vue'),
        meta: { title: '公告' },
      },
    ],
  },
  {
    path: '/manager',
    component: () => import('@/layouts/ManagerLayout.vue'),
    // 经理布局下的所有子路由只能由 manager 角色访问。
    meta: { requiresAuth: true, role: 'manager' },
    children: [
      {
        path: '',
        redirect: '/manager/dashboard',
      },
      {
        path: 'dashboard',
        name: 'manager-dashboard',
        component: () => import('@/views/manager/Dashboard.vue'),
        meta: { title: '经理工作台' },
      },
      {
        path: 'employees',
        name: 'manager-employees',
        component: () => import('@/views/manager/Employees.vue'),
        meta: { title: '员工管理' },
      },
      {
        path: 'attendance',
        name: 'manager-attendance',
        component: () => import('@/views/manager/Attendance.vue'),
        meta: { title: '考勤管理' },
      },
      {
        path: 'salary',
        name: 'manager-salary',
        component: () => import('@/views/manager/Salary.vue'),
        meta: { title: '薪资管理' },
      },
      {
        path: 'leave',
        name: 'manager-leave',
        component: () => import('@/views/manager/LeaveApproval.vue'),
        meta: { title: '请假审批' },
      },
      {
        path: 'leave-types',
        name: 'manager-leave-types',
        component: () => import('@/views/manager/LeaveTypes.vue'),
        meta: { title: '请假类型' },
      },
      {
        path: 'notice',
        name: 'manager-notice',
        component: () => import('@/views/manager/Notice.vue'),
        meta: { title: '公告管理' },
      },
    ],
  },
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 页面切换后回到顶部，避免长表格滚动位置被保留。
  scrollBehavior: () => ({ top: 0 }),
})

// 全局前置守卫：每次路由切换前执行登录校验和角色校验。
router.beforeEach(async (to) => {
  const userStore = useUserStore()
  const isPublic = to.meta.public === true
  const requiresAuth = to.matched.some(
    (record) => record.meta.requiresAuth === true,
  )

  if (!isPublic && requiresAuth && !userStore.token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (userStore.token && !userStore.user) {
    // 刷新页面后 Pinia 会重新初始化，但 Token 仍保存在 localStorage。
    // 这里调用 /auth/me 恢复用户信息，失败则说明 Token 已失效。
    try {
      await userStore.fetchMe()
    } catch {
      userStore.logout()
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }
  }

  if (to.path === '/login' && userStore.user) {
    // 已登录用户不需要再次看到登录页，直接进入自己的首页。
    return userStore.user.role === 'manager'
      ? '/manager/dashboard'
      : '/employee/dashboard'
  }

  const requiredRole = to.meta.role
  if (requiredRole && userStore.user?.role !== requiredRole) {
    // 角色不匹配时跳回自己的首页，避免员工看到经理菜单或经理进入员工页面。
    return userStore.user?.role === 'manager'
      ? '/manager/dashboard'
      : '/employee/dashboard'
  }

  return true
})

export default router
