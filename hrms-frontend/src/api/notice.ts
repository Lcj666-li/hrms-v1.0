import http from './request'

/**
 * 公告接口。
 *
 * 查看接口所有登录用户都可以使用；发布、编辑、删除接口只允许经理调用。
 */

export interface NoticeRecord {
  id: number
  title: string
  content: string
  author_id: number
  author_name?: string | null
  created_at: string
}

export interface NoticePayload {
  title: string
  content: string
}

// 员工和经理共用：公告列表与详情。

export function getNotices(): Promise<NoticeRecord[]> {
  return http.get<NoticeRecord[]>('/notice')
}

export function getNoticeDetail(id: number): Promise<NoticeRecord> {
  return http.get<NoticeRecord>(`/notice/${id}`)
}

// 仅经理可用：公告维护。

export function createNotice(
  data: NoticePayload,
): Promise<NoticeRecord> {
  return http.post<NoticeRecord>('/manager/notice', data)
}

export function updateNotice(
  id: number,
  data: Partial<NoticePayload>,
): Promise<NoticeRecord> {
  return http.put<NoticeRecord>(`/manager/notice/${id}`, data)
}

export function deleteNotice(
  id: number,
): Promise<{ message: string; id: number }> {
  return http.delete(`/manager/notice/${id}`)
}
