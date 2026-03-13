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
  onComplete: (conversationId?: number) => void,
  token: string,
  onProgress?: (message: string) => void
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
    onmessage: (event) => {
      try {
        const chunk = JSON.parse(event.data)
        if (chunk.error) {
          completed = true
          onError(chunk.error)
        } else if (chunk.done) {
          // Stream completed - call onComplete with conversation_id
          completed = true
          onComplete(chunk.conversation_id)
        } else if (chunk.type === 'progress' && onProgress) {
          // Progress indicator
          onProgress(chunk.message)
        } else if (chunk.content) {
          onChunk(chunk.content)
        }
      } catch (e) {
        // Skip invalid JSON (might be [DONE] from old format)
        if (event.data === '[DONE]') {
          completed = true
          onComplete()
        }
      }
    },
    onerror: (error) => {
      completed = true
      onError(error instanceof Error ? error.message : 'Unknown error')
      // Prevent retry by throwing the error
      throw error
    },
    onclose: () => {
      // Connection closed normally - don't retry
      if (!completed) {
        // If connection closed without completion, treat as error
        onError('Connection closed unexpectedly')
      }
    },
    // Don't open the connection when the page is hidden
    openWhenHidden: false,
  })
}
