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

/** 缺失描述的条目 */
export interface MissingDescriptionItem {
  title: string
  created_at: string
}

/** 缺失描述统计响应 */
export interface MissingDescriptionStats {
  total_items: number
  missing_count: number
  has_description_count: number
  missing_items: MissingDescriptionItem[]
}

/** 任务结果项 */
export interface TaskResult {
  title: string
  task_id: string
  status: string
}

/** 触发抓取任务响应 */
export interface FetchMissingResponse {
  message: string
  total_queued: number
  success_count: number
  failed_count: number
  items: TaskResult[]
}

/** 任务结果项 */
export interface TaskResult {
  title: string
  task_id: string
  status: string
  error?: string
  description_source?: string
  rank?: number
}

/** 热搜抓取条目状态 */
export interface HotSearchFetchItem {
  title: string
  rank: number
  status: 'new' | 'duplicate'
  saved: boolean
}

/** 抓取热搜响应 */
export interface FetchHotSearchResponse {
  message: string
  task_id: string
  limit: number
  status: string
  total_fetched: number
  new_items: number
  cached_items: number
  items: HotSearchFetchItem[]
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

/** 获取缺失描述的统计信息 */
export const getMissingDescriptionStats = () => {
  return request.get<MissingDescriptionStats>('/weibo/cache/missing')
}

/** 手动触发抓取缺失描述的任务 */
export const fetchMissingDescriptions = (params: {
  limit?: number
}) => {
  // 为批量抓取描述设置更长的超时时间（5分钟）
  // 因为需要处理多个热搜，每个都需要 Selenium + LLM 生成
  return request.post<FetchMissingResponse>('/weibo/cache/fetch-missing', null, {
    params,
    timeout: 300000 // 5分钟超时
  })
}

/** 手动触发抓取微博热搜 */
export const fetchHotSearch = (params: {
  limit?: number
}) => {
  return request.post<FetchHotSearchResponse>('/weibo/cache/fetch-hot-search', null, { params })
}
