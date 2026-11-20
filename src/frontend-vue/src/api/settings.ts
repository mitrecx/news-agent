import request from '@/utils/request'

export interface ModelProfile {
  id: string
  name: string
  base_url: string
  model: string
  has_api_key: boolean
  temperature: number
  max_tokens: number
  is_active: boolean
}
export interface ModelProfiles {
  items: ModelProfile[]
  active_id: string | null
}
export interface ModelSettingsInput {
  name: string
  base_url: string
  model: string
  api_key?: string
  temperature: number
  max_tokens: number
}
export interface ConnectionResult {
  success: boolean
  message: string
  latency_ms?: number
}
const endpoint = '/settings/models'
export const getModelProfiles = () => request.get<ModelProfiles>(endpoint)
export const createModelProfile = (data: ModelSettingsInput) =>
  request.post<ModelProfile>(endpoint, data)
export const updateModelProfile = (id: string, data: ModelSettingsInput) =>
  request.put<ModelProfile>(`${endpoint}/${id}`, data)
export const activateModelProfile = (id: string) =>
  request.post<ModelProfiles>(`${endpoint}/${id}/activate`)
export const deleteModelProfile = (id: string) => request.delete<ModelProfiles>(`${endpoint}/${id}`)
export const testSavedModel = (id: string) =>
  request.post<ConnectionResult>(`${endpoint}/${id}/test`, null, { timeout: 30000 })
export const testModelConnection = (data: ModelSettingsInput, profileId?: string) =>
  request.post<ConnectionResult>(
    `${endpoint}/test`,
    { ...data, profile_id: profileId },
    { timeout: 30000 },
  )
export const listModels = (data: ModelSettingsInput, profileId?: string) =>
  request.post<{ models: string[] }>(`${endpoint}/available`, { ...data, profile_id: profileId })
export const getCookieStatus = () => request.get<{ has_cookie: boolean }>('/weibo/cookie-status')
export const saveWeiboCookie = (cookie: string) =>
  request.post<{ success: boolean; message: string }>('/weibo/manual-cookie', { cookie })
