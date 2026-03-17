import request from '@/utils/request'

/** 热搜缓存条目 */
export interface WeiboCacheItem {
  title_hash: string
  title: string
  description: string
  description_source: string
  created_at: string
  updated_at: string
  expires_at: string
}

/** 热搜缓存列表响应 */
export interface WeiboCacheResponse {
  items: WeiboCacheItem[]
  total: number
  limit: number
  offset: number
}

/** 热搜缓存统计信息 */
export interface WeiboCacheStats {
  total_entries: number
  active_entries: number
  expired_entries: number
  created_last_hour: number
  from_weibo: number
  from_llm: number
  from_fallback: number
}

/** 获取热搜缓存列表 */
export const getWeiboCache = (params: { limit?: number; offset?: number; search?: string }) => {
  return request.get<WeiboCacheResponse>('/weibo/cache', { params })
}

/** 获取热搜缓存统计 */
export const getWeiboCacheStats = () => {
  return request.get<WeiboCacheStats>('/weibo/cache/stats')
}

/** 删除过期缓存 */
export const deleteExpiredCache = () => {
  return request.delete<{ message: string; count: number }>('/weibo/cache/expired')
}
