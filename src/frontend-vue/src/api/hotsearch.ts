import request from '@/utils/request'

/** 热搜缓存条目 */
export interface HotSearchCacheItem {
  title_hash: string
  title: string
  description: string
  description_source: string
  created_at: string
  updated_at: string
  expires_at: string
}

/** 热搜缓存响应 */
export interface HotSearchCacheResponse {
  items: HotSearchCacheItem[]
  total: number
  limit: number
  offset: number
}

/** 获取微博热搜缓存（支持时间范围和模糊搜索） */
export const getWeiboHotSearchCache = (params: {
  limit?: number
  offset?: number
  search?: string
  start_date?: string
  end_date?: string
}) => {
  return request.get<HotSearchCacheResponse>('/weibo/cache', { params })
}
