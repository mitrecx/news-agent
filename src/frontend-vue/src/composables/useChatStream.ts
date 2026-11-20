import { ref, onUnmounted } from 'vue'
import { sendChatStream } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { ElMessage } from 'element-plus'

export function useChatStream() {
  const chat = useChatStore()
  const conversations = useConversationStore()
  const auth = useAuthStore()
  const settings = useSettingsStore()
  let controller: AbortController | null = null
  const progressMessage = ref('')

  const stopStreaming = () => {
    controller?.abort()
    controller = null
    chat.setStreaming(false)
    chat.isSending = false
    progressMessage.value = ''
  }
  onUnmounted(stopStreaming)

  const sendMessage = async (message: string) => {
    if (chat.isSending || chat.isStreaming) return
    if (!auth.token) {
      ElMessage.warning('请先登录')
      return
    }
    if (!chat.isConnected) {
      ElMessage.warning('服务尚未连接，请稍后重试')
      return
    }
    if (!settings.model) {
      ElMessage.warning('请先在设置中添加并启用一个模型')
      return
    }
    const requestController = new AbortController()
    controller = requestController
    chat.isSending = true
    chat.setStreaming(true)
    chat.addMessage({ role: 'user', content: message })
    chat.addMessage({ role: 'assistant', content: '' })
    const responseIndex = chat.messages.length - 1
    let response = ''
    progressMessage.value = '正在思考…'
    try {
      await sendChatStream(
        { message, conversation_id: chat.conversationId ?? undefined },
        (chunk) => {
          response += chunk
          if (!requestController.signal.aborted) {
            chat.messages[responseIndex]!.content = response
            progressMessage.value = ''
          }
        },
        (error) => {
          if (!requestController.signal.aborted) {
            chat.messages[responseIndex]!.content = error
            progressMessage.value = ''
            ElMessage.error('本次请求失败，请检查模型连接')
          }
        },
        (id) => {
          if (id && !requestController.signal.aborted) {
            chat.setConversationId(id)
            conversations.selectConversation(id)
            conversations.fetchConversations()
          }
        },
        auth.token,
        (message) => {
          progressMessage.value = message
        },
        requestController.signal,
      )
    } catch {
      if (!requestController.signal.aborted) ElMessage.error('发送失败，请检查服务连接')
    } finally {
      if (controller === requestController) {
        chat.setStreaming(false)
        chat.isSending = false
        controller = null
        progressMessage.value = ''
      }
    }
  }

  const loadConversation = async (id: number) => {
    const api = await import('@/api/conversation')
    try {
      const response = await api.getConversationMessages(id)
      chat.loadMessages(response.data.messages)
      chat.setConversationId(id)
      conversations.selectConversation(id)
    } catch {
      ElMessage.error('加载对话失败')
    }
  }
  const startNewConversation = () => {
    chat.clearMessages()
    chat.setConversationId(null)
    conversations.clearCurrentConversation()
  }
  return {
    sendMessage,
    stopStreaming,
    progressMessage,
    loadConversation,
    startNewConversation,
  }
}
