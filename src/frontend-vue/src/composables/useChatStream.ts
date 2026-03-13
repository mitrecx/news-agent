import { ref } from 'vue'
import { sendChatStream } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import * as conversationApi from '@/api/conversation'

export function useChatStream() {
  const chatStore = useChatStore()
  const conversationStore = useConversationStore()
  const authStore = useAuthStore()
  const abortController = ref<AbortController | null>(null)
  const currentResponse = ref('')
  const progressMessage = ref('')

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
    progressMessage.value = ''
    chatStore.setStreaming(true)

    try {
      await sendChatStream(
        {
          message,
          history: chatStore.messages.slice(0, -1),
          conversation_id: chatStore.conversationId ?? undefined,
        },
        // onChunk
        (content: string) => {
          currentResponse.value += content
          chatStore.updateLastMessage(currentResponse.value)
        },
        // onError
        (error: string) => {
          progressMessage.value = ''
          ElMessage.error('发生错误: ' + error)
          chatStore.updateLastMessage('抱歉，发生错误: ' + error)
          chatStore.setStreaming(false)
        },
        // onComplete - receives conversation_id
        async (convId?: number) => {
          progressMessage.value = ''
          chatStore.setStreaming(false)

          if (convId) {
            chatStore.setConversationId(convId)
            conversationStore.selectConversation(convId)

            // Fetch and add conversation details if not already in list
            const exists = conversationStore.conversations.some(c => c.id === convId)
            if (!exists) {
              try {
                const convResponse = await conversationApi.getConversation(convId)
                conversationStore.addConversation(convResponse.data)
              } catch (error) {
                console.error('Failed to fetch conversation details:', error)
              }
            } else {
              // Update existing conversation timestamp
              conversationStore.updateConversationTimestamp(convId)
            }
          }
        },
        authStore.token,
        (message: string) => {
          progressMessage.value = message
        }
      )
    } catch (error) {
      progressMessage.value = ''
      ElMessage.error('发送消息失败')
      chatStore.setStreaming(false)
    }
  }

  /** Load conversation history */
  const loadConversation = async (conversationId: number) => {
    try {
      const response = await conversationApi.getConversationMessages(conversationId)
      chatStore.loadMessages(response.data.messages)
      chatStore.setConversationId(conversationId)
      conversationStore.selectConversation(conversationId)
      return true
    } catch (error) {
      ElMessage.error('加载对话失败')
      return false
    }
  }

  /** Start new conversation */
  const startNewConversation = () => {
    chatStore.clearMessages()
    chatStore.setConversationId(null)
    conversationStore.clearCurrentConversation()
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
    loadConversation,
    startNewConversation,
    stopStreaming,
    progressMessage,
  }
}
