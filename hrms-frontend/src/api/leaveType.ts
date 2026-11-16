import http from './request'

/**
 * 请假类型接口。
 *
 * 员工只需要读取启用中的类型；经理可以查看全部类型并维护启用状态。
 * 已被请假记录引用的类型不提供删除接口，停用后才能从员工下拉框中消失。
 */

export interface LeaveType {
  id: number
  code: string
  name: string
  is_paid: boolean
  max_days_per_year: number | null
  requires_approval: boolean
  is_active: boolean
  created_at: string
}

export interface LeaveTypeCreatePayload {
  code: string
  name: string
  is_paid: boolean
  max_days_per_year: number | null
  requires_approval: boolean
  is_active: boolean
}

export type LeaveTypeUpdatePayload = Partial<LeaveTypeCreatePayload>

export function getActiveLeaveTypes(): Promise<LeaveType[]> {
  return http.get<LeaveType[]>('/leave-types')
}

export function getLeaveTypes(): Promise<LeaveType[]> {
  return http.get<LeaveType[]>('/manager/leave-types')
}

export function createLeaveType(
  data: LeaveTypeCreatePayload,
): Promise<LeaveType> {
  return http.post<LeaveType>('/manager/leave-types', data)
}

export function updateLeaveType(
  id: number,
  data: LeaveTypeUpdatePayload,
): Promise<LeaveType> {
  return http.put<LeaveType>(`/manager/leave-types/${id}`, data)
}
