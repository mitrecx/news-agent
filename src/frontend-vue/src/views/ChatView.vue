<template>
  <div class="chat-view">
    <!-- 顶部导航栏 -->
    <AppNav :full-width="true" />

    <!-- 对话内容区域 -->
    <div class="chat-content">
      <!-- 对话侧边栏 -->
      <ConversationSidebar />

      <!-- 主聊天区域 -->
      <div class="chat-main">
        <!-- Messages -->
        <div class="chat-messages" ref="messagesContainer">
          <div v-if="chatStore.messages.length === 0" class="welcome">
            <el-icon size="64" color="#9ca3af"><ChatDotRound /></el-icon>
            <h2>欢迎使用 News Agent</h2>
            <p>基于 DeepSeek 模型的智能对话助手</p>
            <p>支持查询微博热搜</p>
          </div>

          <ChatMessage
            v-for="(message, index) in chatStore.messages"
            :key="index"
            :message="message"
            :is-streaming="chatStore.isStreaming && index === chatStore.messages.length - 1 && message.role === 'assistant'"
          />

          <!-- Progress indicator -->
          <div v-if="progressMessage" class="progress-indicator">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ progressMessage }}</span>
          </div>
        </div>

        <!-- Input -->
        <ChatInput
          ref="chatInputRef"
          :is-streaming="chatStore.isStreaming"
          :is-connected="chatStore.isConnected"
          :messages="chatStore.messages"
          @send="handleSend"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElIcon } from 'element-plus'
import { ChatDotRound, Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useChatStream } from '@/composables/useChatStream'
import { useHealthCheck } from '@/composables/useHealthCheck'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import AppNav from '@/components/AppNav.vue'

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()
const conversationStore = useConversationStore()
const { sendMessage, progressMessage, loadConversation } = useChatStream()

const messagesContainer = ref<HTMLElement>()
const chatInputRef = ref<InstanceType<typeof ChatInput>>()

// Load conversations on mount
onMounted(async () => {
  console.log('[ChatView] ✅ Component mounted')
  await conversationStore.fetchConversations()

  // Restore the last selected conversation if exists
  if (conversationStore.currentConversationId) {
    const savedId = conversationStore.currentConversationId
    const exists = conversationStore.conversations.some(c => c.id === savedId)

    if (exists) {
      console.log('[ChatView] 🔄 Restoring conversation:', savedId)
      await loadConversation(savedId)
    } else {
      console.log('[ChatView] ⚠️ Saved conversation not found, clearing')
      conversationStore.clearCurrentConversation()
    }
  }

  // Auto-focus input after conversation is loaded/restored
  await nextTick()
  chatInputRef.value?.focus()
})

onUnmounted(() => {
  console.log('[ChatView] 🗑️ Component unmounted')
})

// Auto-scroll to bottom
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

// Watch for conversation changes to ensure input history is updated
watch(
  () => chatStore.conversationId,
  async (newId, oldId) => {
    if (newId !== oldId) {
      console.log('[ChatView] 🔄 Conversation changed from', oldId, 'to', newId)
      // Auto-focus input after conversation switches
      await nextTick()
      chatInputRef.value?.focus()
    }
  }
)

const handleSend = (message: string) => {
  console.log('[ChatView] 📥 Received send event:', message)
  sendMessage(message)
}

// Start health check
useHealthCheck()
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f9fafb;
}

.chat-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.welcome {
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.welcome h2 {
  font-size: 20px;
  margin: 16px 0 8px;
  color: #6b7280;
}

.welcome p {
  font-size: 14px;
  margin: 4px 0;
}

.chat-message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.chat-message.assistant {
  align-self: flex-start;
}

.chat-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  font-weight: 500;
}

.assistant .avatar {
  background: #e5e7eb;
  color: #6b7280;
}

.user .avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.assistant .bubble {
  background: #f3f4f6;
  color: #1f2937;
}

.user .bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f3f4f6;
  border-radius: 8px;
  font-size: 14px;
  color: #6b7280;
  margin: 0 auto;
  max-width: fit-content;
}

.progress-indicator .el-icon {
  color: #667eea;
  font-size: 18px;
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
