<template>
  <div class="chat-view">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-content">
        <div>
          <h1>News Agent</h1>
          <p>基于 LangChain + DeepSeek 的新闻助手</p>
        </div>
        <div class="header-actions">
          <div class="status-indicator">
            <span :class="['status-dot', { connected: chatStore.isConnected }]"></span>
            <span>{{ chatStore.isConnected ? '已连接' : 'Agent 未就绪' }}</span>
          </div>
          <el-dropdown trigger="click">
            <div class="user-dropdown">
              <el-icon><User /></el-icon>
              <span>{{ authStore.user?.username }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

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
      />

      <!-- Streaming cursor -->
      <div v-if="chatStore.isStreaming" class="chat-message assistant">
        <div class="avatar">AI</div>
        <div class="bubble">
          {{ currentContent }}
          <span class="cursor"></span>
        </div>
      </div>
    </div>

    <!-- Input -->
    <ChatInput
      :is-streaming="chatStore.isStreaming"
      :is-connected="chatStore.isConnected"
      @send="handleSend"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElDropdown, ElDropdownMenu, ElDropdownItem, ElIcon } from 'element-plus'
import { User, SwitchButton, ChatDotRound } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useChatStream } from '@/composables/useChatStream'
import { useHealthCheck } from '@/composables/useHealthCheck'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()
const { sendMessage } = useChatStream()

const messagesContainer = ref<HTMLElement>()
const currentContent = ref('')

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

// Track current streaming content
watch(
  () => chatStore.messages,
  (messages) => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'assistant') {
        currentContent.value = lastMessage.content
      }
    }
  },
  { deep: true }
)

const handleSend = (message: string) => {
  sendMessage(message)
}

const handleLogout = () => {
  authStore.logout()
  chatStore.clearMessages()
  router.push('/login')
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

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.chat-header h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 4px;
}

.chat-header p {
  font-size: 14px;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f87171;
}

.status-dot.connected {
  background: #4ade80;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: rgba(255, 255, 255, 0.2);
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

.cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #667eea;
  animation: blink 1s infinite;
  margin-left: 2px;
  vertical-align: text-bottom;
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
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
