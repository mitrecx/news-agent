import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage } from '@/types'

export const useChatStore = defineStore('chat', () => {
  /** State */
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isConnected = ref(false)

  /** Actions */
  const addMessage = (message: ChatMessage) => {
    messages.value.push(message)
  }

  const updateLastMessage = (content: string) => {
    if (messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1]
      if (lastMessage.role === 'assistant') {
        lastMessage.content = content
      }
    }
  }

  const setStreaming = (streaming: boolean) => {
    isStreaming.value = streaming
  }

  const setConnected = (connected: boolean) => {
    isConnected.value = connected
  }

  const clearMessages = () => {
    messages.value = []
  }

  return {
    messages,
    isStreaming,
    isConnected,
    addMessage,
    updateLastMessage,
    setStreaming,
    setConnected,
    clearMessages,
  }
})
