import { ref } from 'vue'
import { sendChatStream } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

export function useChatStream() {
  const chatStore = useChatStore()
  const authStore = useAuthStore()
  const abortController = ref<AbortController | null>(null)
  const currentResponse = ref('')

  /** Send message with streaming */
  const sendMessage = async (message: string) => {
    if (chatStore.isStreaming) {
      stopStreaming()
      return
    }

    if (!authStore.token) {
      ElMessage.error('请先登录')
      return
    }

    if (!chatStore.isConnected) {
      ElMessage.error('Agent 未就绪，请稍后重试')
      return
    }

    // Add user message
    chatStore.addMessage({ role: 'user', content: message })

    // Add empty assistant message
    chatStore.addMessage({ role: 'assistant', content: '' })
    currentResponse.value = ''
    chatStore.setStreaming(true)

    try {
      await sendChatStream(
        {
          message,
          history: chatStore.messages.slice(0, -1), // Exclude the empty assistant message
        },
        // onChunk
        (content: string) => {
          currentResponse.value += content
          chatStore.updateLastMessage(currentResponse.value)
        },
        // onError
        (error: string) => {
          ElMessage.error('发生错误: ' + error)
          chatStore.updateLastMessage('抱歉，发生错误: ' + error)
          chatStore.setStreaming(false)
        },
        // onComplete
        () => {
          chatStore.setStreaming(false)
        },
        authStore.token
      )
    } catch (error) {
      ElMessage.error('发送消息失败')
      chatStore.setStreaming(false)
    }
  }

  /** Stop streaming */
  const stopStreaming = () => {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }

    if (currentResponse.value) {
      chatStore.updateLastMessage(currentResponse.value + ' (已中断)')
    }

    chatStore.setStreaming(false)
  }

  return {
    sendMessage,
    stopStreaming,
  }
}
