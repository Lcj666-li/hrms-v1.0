import axios from 'axios'
import type {
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'

/**
 * Axios 统一请求模块。
 *
 * 页面只关心“调用哪个接口、拿到什么数据”，下面这些事情全部在这里统一处理：
 * 1. 拼接 /api 前缀；
 * 2. 自动携带 JWT；
 * 3. 统一弹出错误提示；
 * 4. 遇到 401 时清理登录状态并跳转登录页。
 */

export const TOKEN_STORAGE_KEY = 'hrms_token'

interface ApiErrorBody {
  detail?: string
  message?: string
}

// 所有业务请求共用的 Axios 实例。
// baseURL 默认使用 /api，开发环境由 Vite 代理到 FastAPI，生产环境可改 VITE_API_BASE_URL。
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

// 请求拦截器：发请求前自动从 localStorage 读取 Token，
// 按后端 OAuth2/Bearer 约定写入 Authorization 请求头。
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
)

// 响应拦截器：成功时直接返回后端 JSON 的 data 部分；
// 失败时统一显示中文错误，并处理登录过期。
service.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorBody>) => {
    const statusCode = error.response?.status
    const requestUrl = error.config?.url ?? ''
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '请求失败，请稍后重试'

    // 登录接口本身的 401 表示“用户名或密码错误”，应留在登录页显示提示，
    // 不能触发“登录失效”跳转逻辑。
    if (statusCode === 401 && !requestUrl.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem('hrms_user')
      if (window.location.pathname !== '/login') {
        window.location.replace('/login')
      }
    }

    ElMessage.error(message)
    return Promise.reject(error)
  },
)

// 对 Axios 做一层轻量包装，让页面代码可以写成 http.get<T>()，
// 同时保留完整的 TypeScript 返回类型。
const http = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, config) as unknown as Promise<T>
  },
  post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    return service.post(url, data, config) as unknown as Promise<T>
  },
  put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    return service.put(url, data, config) as unknown as Promise<T>
  },
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, config) as unknown as Promise<T>
  },
}

export default http
