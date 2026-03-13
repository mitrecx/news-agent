import request from '@/utils/request'
import type { Conversation } from '@/types'

/** Get conversation list */
export const listConversations = (params?: { limit?: number; offset?: number }) => {
  return request.get<Conversation[]>('/conversations', { params })
}

/** Get single conversation */
export const getConversation = (id: number) => {
  return request.get<Conversation>(`/conversations/${id}`)
}

/** Rename conversation */
export const updateConversation = (id: number, title: string) => {
  return request.put<Conversation>(`/conversations/${id}`, { title })
}

/** Delete conversation */
export const deleteConversation = (id: number) => {
  return request.delete<{ message: string }>(`/conversations/${id}`)
}

/** Get conversation messages */
export const getConversationMessages = (id: number) => {
  return request.get<{ conversation_id: number; messages: any[] }>(
    `/conversations/${id}/messages`
  )
}
