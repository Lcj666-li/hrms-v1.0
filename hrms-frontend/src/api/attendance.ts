import http from './request'

/**
 * 考勤接口。
 *
 * 同时覆盖员工端（本人打卡、本人月度记录）和经理端（全员查询、月度统计）。
 * 后端会根据当前登录用户的角色再次校验权限。
 */

export type AttendanceStatus =
  | 'normal'
  | 'late'
  | 'early'
  | 'late_early'
  | 'missing'
  | 'absent'

export interface AttendanceRecord {
  id: number
  user_id: number
  user_name?: string | null
  department?: string | null
  date: string
  check_in?: string | null
  check_out?: string | null
  status: AttendanceStatus
  remark?: string | null
  created_at: string
}

export interface AttendanceCheckResponse {
  message: string
  data: AttendanceRecord
}

export interface AttendanceStat {
  month: string
  total_records: number
  normal: number
  late: number
  early: number
  late_early: number
  missing: number
  absent: number
  attendance_rate: number
}

export interface AttendanceQuery {
  date?: string
  department?: string
  name?: string
}

// 员工打卡：上班和下班分别调用独立接口。

export function checkIn(): Promise<AttendanceCheckResponse> {
  return http.post<AttendanceCheckResponse>('/attendance/check-in')
}

export function checkOut(): Promise<AttendanceCheckResponse> {
  return http.post<AttendanceCheckResponse>('/attendance/check-out')
}

// 员工查看本人考勤。

export function getMyAttendance(
  month?: string,
): Promise<AttendanceRecord[]> {
  return http.get<AttendanceRecord[]>('/attendance/my', {
    params: { month },
  })
}

export function getTodayAttendance(): Promise<AttendanceRecord | null> {
  return http.get<AttendanceRecord | null>('/attendance/today')
}

// 经理查看全员考勤和月度统计。

export function getAllAttendance(
  params: AttendanceQuery,
): Promise<AttendanceRecord[]> {
  return http.get<AttendanceRecord[]>('/manager/attendance', { params })
}

export function getAttendanceStat(
  month: string,
): Promise<AttendanceStat> {
  return http.get<AttendanceStat>('/manager/attendance/stat', {
    params: { month },
  })
}
