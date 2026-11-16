import http from './request'

/**
 * 薪资接口。
 *
 * 后端统一计算实发工资，前端只负责提交薪资组成项。
 * 员工端只能看到状态为 issued 的本人记录。
 */

export type SalaryStatus = 'draft' | 'issued'

export interface SalaryRecord {
  id: number
  user_id: number
  user_name?: string | null
  department?: string | null
  salary_month: string
  base_salary: number
  attendance_deduction: number
  leave_deduction: number
  bonus: number
  social_security: number
  tax: number
  actual_salary: number
  status: SalaryStatus
  created_by: number
  created_by_name?: string | null
  issued_at?: string | null
  created_at: string
}

export interface SalaryCreatePayload {
  user_id: number
  salary_month: string
  base_salary: number
  attendance_deduction: number
  leave_deduction: number
  bonus: number
  social_security: number
  tax: number
}

export type SalaryUpdatePayload = Partial<SalaryCreatePayload>

export interface SalaryQuery {
  month?: string
  user_id?: number
  status?: SalaryStatus
}

export function getMySalaries(month?: string): Promise<SalaryRecord[]> {
  return http.get<SalaryRecord[]>('/salary/my', {
    params: { month },
  })
}

export function getSalaryRecords(
  params: SalaryQuery,
): Promise<SalaryRecord[]> {
  return http.get<SalaryRecord[]>('/manager/salary', { params })
}

export function createSalaryRecord(
  data: SalaryCreatePayload,
): Promise<SalaryRecord> {
  return http.post<SalaryRecord>('/manager/salary', data)
}

export function updateSalaryRecord(
  id: number,
  data: SalaryUpdatePayload,
): Promise<SalaryRecord> {
  return http.put<SalaryRecord>(`/manager/salary/${id}`, data)
}

export function issueSalaryRecord(id: number): Promise<SalaryRecord> {
  return http.put<SalaryRecord>(`/manager/salary/${id}/issue`)
}
