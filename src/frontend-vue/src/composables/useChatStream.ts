import { ref, onUnmounted } from 'vue'
import { sendChatStream } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import * as conversationApi from '@/api/conversation'

// Generate unique instance ID for debugging
const instanceId = Math.random().toString(36).substring(2, 9)
console.log(`[useChatStream] 🆔 Instance created: ${instanceId}`)

export function useChatStream() {
  const chatStore = useChatStore()
  const conversationStore = useConversationStore()
  const authStore = useAuthStore()
  const abortController = ref<AbortController | null>(null)
  const currentResponse = ref('')
  const progressMessage = ref('')
  const isSending = ref(false) // Track if a message is being sent

  // Cleanup on component unmount
  onUnmounted(() => {
    console.log(`[useChatStream:${instanceId}] 🗑️ Instance unmounted`)
    // Stop any ongoing request
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    // Reset state
    isSending.value = false
    currentResponse.value = ''
    progressMessage.value = ''
  })

  /** Send message with streaming */
  const sendMessage = async (message: string) => {
    // Prevent duplicate requests
    if (isSending.value) {
      console.log(`[useChatStream:${instanceId}] ⚠️ Request already in progress, ignoring duplicate send`, {
        message,
        isSending: isSending.value,
        isStreaming: chatStore.isStreaming
      })
      return
    }

    if (chatStore.isStreaming) {
      console.log(`[useChatStream:${instanceId}] ⚠️ Already streaming, stopping previous stream`)
      stopStreaming()
      // Give it a moment to stop before starting new request
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    console.log(`[useChatStream:${instanceId}] 📤 Sending message:`, message)

    if (!authStore.token) {
      ElMessage.error('请先登录')
      return
    }

    if (!chatStore.isConnected) {
      ElMessage.error('Agent 未就绪，请稍后重试')
      return
    }

    isSending.value = true

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
    } finally {
      isSending.value = false
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
