import request from '@/utils/request'

/** 热搜缓存条目 */
export interface HotSearchCacheItem {
  title_hash: string
  url?: string
  title: string
  description: string | null
  description_source: string | null
  created_at: string
  updated_at: string
  expires_at: string
  summary_status: 'ready' | 'queued' | 'processing' | 'retrying'
  summary_error?: string | null
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
}

export interface SingleSummaryResponse {
  status: 'queued' | 'cached'
  item: HotSearchCacheItem
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
  description_tasks_queued: number
  items: HotSearchFetchItem[]
}

/** 获取微博热搜缓存（支持时间范围和模糊搜索） */
export const getWeiboHotSearchCache = (params: {
  limit?: number
  offset?: number
  search?: string
  start_date?: string
  end_date?: string
  status?: 'all' | 'ready' | 'pending'
}) => {
  return request.get<HotSearchCacheResponse>('/weibo/cache', { params })
}

export const getStoryDetail = (titleHash: string) => {
  return request.get<HotSearchCacheItem>(`/weibo/cache/${encodeURIComponent(titleHash)}`)
}

/** 获取缺失描述的统计信息 */
export const getMissingDescriptionStats = () => {
  return request.get<MissingDescriptionStats>('/weibo/cache/missing')
}

/** 有描述的热搜条目 */
export interface HasDescriptionItem {
  title: string
  description: string
  description_source: string
  created_at: string
  updated_at: string
}

/** 有描述的热搜响应 */
export interface HasDescriptionResponse {
  items: HasDescriptionItem[]
}

/** 获取有描述的热搜列表 */
export const getHasDescriptionItems = (params?: { limit?: number }) => {
  return request.get<HasDescriptionResponse>('/weibo/cache/has-description', {
    params,
  })
}

/** 手动触发抓取缺失描述的任务 */
export const fetchMissingDescriptions = (params: { limit?: number }) => {
  return request.post<FetchMissingResponse>('/weibo/cache/fetch-missing', null, {
    params,
  })
}

/** 将指定资讯加入摘要队列。 */
export const fetchStorySummary = (titleHash: string) => {
  return request.post<SingleSummaryResponse>(
    `/weibo/cache/${encodeURIComponent(titleHash)}/summary`,
    null,
  )
}

/** 手动触发抓取微博热搜 */
export const fetchHotSearch = (params: { limit?: number }) => {
  return request.post<FetchHotSearchResponse>('/weibo/cache/fetch-hot-search', null, { params })
}

/** 删除单个热搜 */
export const deleteHotSearch = (title: string) => {
  return request.delete<{ message: string; title: string }>(
    `/weibo/cache/item/${encodeURIComponent(title)}`,
  )
}

/** 批量删除热搜 */
export const batchDeleteHotSearches = (titles: string[]) => {
  return request.delete<{ message: string; count: number; requested: number }>(
    '/weibo/cache/batch',
    { data: { titles } },
  )
}
