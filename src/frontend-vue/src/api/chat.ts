import request from '@/utils/request'
import type { ChatRequest, ChatResponse, HealthResponse } from '@/types'

/** Health check */
export const healthCheck = () => {
  return request.get<HealthResponse>('/health', { baseURL: '' })
}

/** Send chat message */
export const sendChat = (data: ChatRequest) => {
  return request.post<ChatResponse>('/chat', data)
}

/** Send chat message with streaming */
export const sendChatStream = async (
  data: ChatRequest,
  onChunk: (content: string) => void,
  onError: (error: string) => void,
  onComplete: () => void,
  token: string
) => {
  const { fetchEventSource } = await import('@microsoft/fetch-event-source')

  await fetchEventSource('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
    onmessage: (event) => {
      if (event.data === '[DONE]') {
        onComplete()
        return
      }

      try {
        const chunk = JSON.parse(event.data)
        if (chunk.error) {
          onError(chunk.error)
        } else if (chunk.content) {
          onChunk(chunk.content)
        }
      } catch (e) {
        // Skip invalid JSON
      }
    },
    onerror: (error) => {
      onError(error instanceof Error ? error.message : 'Unknown error')
    },
  })
}
