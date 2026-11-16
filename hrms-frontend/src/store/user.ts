import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getMe,
  login as loginRequest,
  type AuthUser,
  type LoginParams,
  type LoginResponse,
} from '@/api/auth'
import { TOKEN_STORAGE_KEY } from '@/api/request'

/**
 * 登录状态仓库。
 *
 * Token 和 user 同时保存在两个地方：
 * - Pinia 内存：页面运行期间快速读取；
 * - localStorage：浏览器刷新后仍然保持登录。
 */

const USER_STORAGE_KEY = 'hrms_user'

// 读取本地用户信息时做一次 JSON 容错，避免损坏数据导致整个应用无法启动。
function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY)
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem(TOKEN_STORAGE_KEY) ?? '')
  const user = ref<AuthUser | null>(readStoredUser())

  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed(() => user.value?.role ?? null)

  function setAuth(result: LoginResponse) {
    // 登录成功后同时更新响应式状态和本地持久化数据。
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token)
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(result.user))
  }

  function logout() {
    // 退出时清理全部认证信息，防止下一位使用者读取到上一位用户的状态。
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
  }

  async function login(params: LoginParams) {
    const result = await loginRequest(params)
    setAuth(result)
    return result
  }

  async function fetchMe() {
    // 用于刷新页面后根据 Token 重新获取当前用户信息。
    const currentUser = await getMe()
    user.value = currentUser
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(currentUser))
    return currentUser
  }

  return {
    token,
    user,
    isLoggedIn,
    role,
    setAuth,
    logout,
    login,
    fetchMe,
  }
})
