import http from './request'

/**
 * 请假接口。
 *
 * 员工端负责提交、查看和撤销；经理端负责查看待审批、审批历史和执行审批。
 * 所有状态变化都由后端校验，前端只根据状态控制按钮显示。
 */

export type LeaveStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'cancelled'

export interface LeaveRecord {
  id: number
  user_id: number
  user_name?: string | null
  department?: string | null
  leave_type_id: number
  leave_type_name?: string | null
  leave_type_is_paid?: boolean | null
  start_date: string
  end_date: string
  reason: string
  status: LeaveStatus
  approver_id?: number | null
  approver_name?: string | null
  approve_comment?: string | null
  approve_time?: string | null
  created_at: string
}

export interface LeaveCreatePayload {
  leave_type_id: number
  start_date: string
  end_date: string
  reason: string
}

export interface LeaveReviewPayload {
  comment?: string | null
}

// ---------- 员工请假 ----------

export function createLeave(
  data: LeaveCreatePayload,
): Promise<LeaveRecord> {
  return http.post<LeaveRecord>('/leave', data)
}

export function getMyLeaves(
  status?: LeaveStatus,
): Promise<LeaveRecord[]> {
  return http.get<LeaveRecord[]>('/leave/my', {
    params: { status },
  })
}

export function cancelLeave(
  id: number,
): Promise<{ message: string; id: number }> {
  return http.put(`/leave/${id}/cancel`)
}

// ---------- 经理审批 ----------

export function getPendingLeaves(): Promise<LeaveRecord[]> {
  return http.get<LeaveRecord[]>('/manager/leave/pending')
}

export function getLeaveHistory(): Promise<LeaveRecord[]> {
  return http.get<LeaveRecord[]>('/manager/leave/history')
}

export function approveLeave(
  id: number,
  data: LeaveReviewPayload,
): Promise<LeaveRecord> {
  return http.put<LeaveRecord>(`/manager/leave/${id}/approve`, data)
}

export function rejectLeave(
  id: number,
  data: LeaveReviewPayload,
): Promise<LeaveRecord> {
  return http.put<LeaveRecord>(`/manager/leave/${id}/reject`, data)
}
