import request from '@/utils/request'

/** 实时热搜条目 */
export interface HotSearchItem {
  rank: number
  title: string
  description: string
  metrics?: any
}

/** 热搜响应 */
export interface HotSearchResponse {
  items: HotSearchItem[]
  total: number
  limit: number
  raw: string
}

/** 获取实时微博热搜 */
export const getWeiboHotSearch = (params: { limit?: number }) => {
  return request.get<HotSearchResponse>('/weibo/hot', { params })
}
