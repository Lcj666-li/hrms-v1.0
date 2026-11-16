import http from './request'

/**
 * 认证、个人资料和员工管理接口。
 *
 * 页面不直接拼接 URL，而是调用这里的函数，这样接口路径变化时只需要改一个文件。
 */

export type UserRole = 'employee' | 'manager'

export interface AuthUser {
  id: number
  name: string
  role: UserRole
}

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface UserProfile extends AuthUser {
  username: string
  gender?: string | null
  phone?: string | null
  email?: string | null
  department?: string | null
  position?: string | null
  hire_date?: string | null
  is_active: boolean
  created_at: string
}

export interface ProfileUpdatePayload {
  name?: string
  gender?: string | null
  phone?: string | null
  email?: string | null
}

export interface EmployeeCreatePayload {
  username: string
  password: string
  name: string
  gender?: string | null
  phone?: string | null
  email?: string | null
  department?: string | null
  position?: string | null
  hire_date?: string | null
  is_active?: boolean
}

export interface EmployeeUpdatePayload {
  username?: string
  password?: string
  name?: string
  gender?: string | null
  phone?: string | null
  email?: string | null
  department?: string | null
  position?: string | null
  hire_date?: string | null
  is_active?: boolean
}

// ---------- 认证 ----------

export function login(data: LoginParams): Promise<LoginResponse> {
  return http.post<LoginResponse>('/auth/login', data)
}

export function getMe(): Promise<AuthUser> {
  return http.get<AuthUser>('/auth/me')
}

// ---------- 员工个人资料 ----------

export function getProfile(): Promise<UserProfile> {
  return http.get<UserProfile>('/user/profile')
}

export function updateProfile(
  data: ProfileUpdatePayload,
): Promise<UserProfile> {
  return http.put<UserProfile>('/user/profile', data)
}

// ---------- 经理维护员工 ----------

export function getEmployees(): Promise<UserProfile[]> {
  return http.get<UserProfile[]>('/manager/employees')
}

export function createEmployee(
  data: EmployeeCreatePayload,
): Promise<UserProfile> {
  return http.post<UserProfile>('/manager/employees', data)
}

export function updateEmployee(
  id: number,
  data: EmployeeUpdatePayload,
): Promise<UserProfile> {
  return http.put<UserProfile>(`/manager/employees/${id}`, data)
}

export function toggleEmployeeStatus(
  id: number,
): Promise<{ message: string; id: number; is_active: boolean }> {
  return http.put(`/manager/employees/${id}/disable`)
}
