import request from '@/utils/request'
import type { ChatRequest, ChatResponse, HealthResponse } from '@/types'
export const healthCheck = () => request.get<HealthResponse>('/health', { baseURL: '' })
export const sendChat = (data: ChatRequest) => request.post<ChatResponse>('/chat', data)
export const sendChatStream = async (
  data: ChatRequest,
  onChunk: (content: string) => void,
  onError: (error: string) => void,
  onComplete: (id?: number) => void,
  token: string,
  onProgress?: (message: string) => void,
  signal?: AbortSignal,
) => {
  const { fetchEventSource } = await import('@microsoft/fetch-event-source')
  let completed = false
  await fetchEventSource('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
    signal,
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok)
        throw new Error(
          response.status === 401 ? '登录已过期，请重新登录' : '请求失败，请检查模型设置',
        )
    },
    onmessage(event) {
      if (completed || signal?.aborted) return
      let chunk
      try {
        chunk = JSON.parse(event.data)
      } catch {
        return
      }
      if (chunk.error) {
        completed = true
        onError(chunk.error)
      } else if (chunk.done) {
        completed = true
        onComplete(chunk.conversation_id)
      } else if (chunk.content) onChunk(chunk.content)
      else if (chunk.type === 'progress' || chunk.type === 'start') onProgress?.(chunk.message)
    },
    onerror(error) {
      if (!signal?.aborted) onError(error instanceof Error ? error.message : '连接中断，请稍后重试')
      throw error
    },
    onclose() {
      if (!completed && !signal?.aborted) throw new Error('连接中断，请重试')
    },
  })
}
