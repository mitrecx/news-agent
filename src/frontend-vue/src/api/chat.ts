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
  let aborted = false

  await fetchEventSource('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
    onmessage: (event) => {
      if (aborted) return

      try {
        const chunk = JSON.parse(event.data)
        if (chunk.error) {
          completed = true
          aborted = true
          onError(chunk.error)
        } else if (chunk.done) {
          // Stream completed - call onComplete with conversation_id
          completed = true
          console.log('[chat.ts] ✅ Stream completed successfully')
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
          console.log('[chat.ts] ✅ Stream completed with [DONE]')
          onComplete()
        }
      }
    },
    onerror: (error) => {
      if (aborted) return

      completed = true
      aborted = true
      console.error('[chat.ts] ❌ Stream error:', error)
      onError(error instanceof Error ? error.message : 'Unknown error')
      // Prevent retry by throwing the error
      throw error
    },
    onclose: () => {
      // Connection closed normally - don't retry
      if (!completed && !aborted) {
        // If connection closed without completion, treat as error
        // IMPORTANT: throw to prevent retry by fetch-event-source
        const errorMsg = 'Connection closed unexpectedly'
        console.error('[chat.ts] ⚠️ Connection closed without completion signal')
        onError(errorMsg)
        throw new Error(errorMsg)
      } else {
        console.log('[chat.ts] 🔌 Connection closed normally')
      }
    },
    // Don't open the connection when the page is hidden
    openWhenHidden: false,
  })
}
