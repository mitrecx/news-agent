<template>
  <div class="chat-input">
    <el-input
      ref="inputRef"
      v-model="inputMessage"
      type="textarea"
      :rows="1"
      :autosize="{ minRows: 1, maxRows: 4 }"
      placeholder="输入消息..."
      :disabled="isStreaming || !isConnected"
      @keydown="handleKeydown"
      @input="handleInput"
    />
    <el-button
      :type="isStreaming ? 'danger' : 'primary'"
      :disabled="!inputMessage.trim() || !isConnected"
      :loading="isStreaming"
      @click="handleSend"
    >
      {{ isStreaming ? '停止' : '发送' }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElInput, ElButton } from 'element-plus'
import type { ChatMessage } from '@/types'

const props = defineProps<{
  isStreaming: boolean
  isConnected: boolean
  messages: ChatMessage[]
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const inputMessage = ref('')
const inputRef = ref<InstanceType<typeof ElInput>>()

// Message history for up/down arrow navigation
const messageHistory = ref<string[]>([])
const historyIndex = ref(-1)
const isNavigatingHistory = ref(false)

// Constants
const MAX_HISTORY_SIZE = 10

// Extract user messages from conversation to build history
const buildHistoryFromMessages = (messages: ChatMessage[]) => {
  const userMessages = messages
    .filter(msg => msg.role === 'user')
    .map(msg => msg.content.trim())
    .filter((msg, index, arr) => msg && msg !== arr[index - 1]) // Remove duplicates

  // Keep only the last MAX_HISTORY_SIZE messages
  return userMessages.slice(-MAX_HISTORY_SIZE)
}

// Load message history from current conversation's messages
onMounted(() => {
  console.log('[ChatInput] ✅ Component mounted')
  messageHistory.value = buildHistoryFromMessages(props.messages)
  console.log('[ChatInput] 📚 Built history from', messageHistory.value.length, 'user messages')
})

onUnmounted(() => {
  console.log('[ChatInput] 🗑️ Component unmounted')
})

// Watch for changes in messages and rebuild history
watch(
  () => props.messages,
  (newMessages, oldMessages) => {
    // Check if the message array reference changed (conversation switched)
    const conversationSwitched = oldMessages !== newMessages

    console.log('[ChatInput] 📝 Messages changed:', {
      conversationSwitched,
      newCount: newMessages.length,
      oldCount: oldMessages?.length,
      isNavigating: isNavigatingHistory.value
    })

    // Always rebuild when conversation switches, otherwise only if not navigating
    if (conversationSwitched || !isNavigatingHistory.value) {
      const newHistory = buildHistoryFromMessages(newMessages)
      // Check if history actually changed
      if (JSON.stringify(newHistory) !== JSON.stringify(messageHistory.value)) {
        messageHistory.value = newHistory
        console.log('[ChatInput] 📚 History updated, now has', messageHistory.value.length, 'messages:', newHistory)
      }
      // Reset navigation state when conversation switches
      if (conversationSwitched) {
        historyIndex.value = -1
        isNavigatingHistory.value = false
        inputMessage.value = ''
        console.log('[ChatInput] 🔄 Navigation state reset for new conversation')
      }
    }
  },
  { flush: 'post' } // Ensure updates happen after DOM updates
)

const handleSend = () => {
  const message = inputMessage.value.trim()
  if (!message || props.isStreaming || !props.isConnected) return

  console.log('[ChatInput] 📤 Emitting send event:', message)
  emit('send', message)

  // Reset history navigation
  historyIndex.value = -1
  inputMessage.value = ''
  isNavigatingHistory.value = false

  // History will be automatically updated when the new message is added to props.messages
}

const handleKeydown = (event: Event | KeyboardEvent) => {
  if (!(event instanceof KeyboardEvent)) return

  // Handle Enter key (send message)
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
    return
  }

  // Handle Arrow Up (previous message)
  if (event.key === 'ArrowUp' && messageHistory.value.length > 0) {
    // Always allow navigation to previous message
    event.preventDefault()
    navigateHistory('up')
    return
  }

  // Handle Arrow Down (next message)
  if (event.key === 'ArrowDown' && messageHistory.value.length > 0) {
    // Always allow navigation to next message
    event.preventDefault()
    navigateHistory('down')
    return
  }
}

const navigateHistory = (direction: 'up' | 'down') => {
  if (direction === 'up') {
    // Go to previous message
    if (historyIndex.value < messageHistory.value.length - 1) {
      historyIndex.value++
      isNavigatingHistory.value = true
      inputMessage.value = messageHistory.value[messageHistory.value.length - 1 - historyIndex.value]
    }
  } else if (direction === 'down') {
    // Go to next message
    if (historyIndex.value > 0) {
      historyIndex.value--
      inputMessage.value = messageHistory.value[messageHistory.value.length - 1 - historyIndex.value]
    } else if (historyIndex.value === 0) {
      // Clear input when going back from the first historical message
      historyIndex.value = -1
      inputMessage.value = ''
    }
  }
}

const handleInput = () => {
  // If user starts typing while navigating history, exit navigation mode
  if (isNavigatingHistory.value) {
    isNavigatingHistory.value = false
    historyIndex.value = -1
  }
  // Auto-resize handled by el-input autosize prop
}

const focus = () => {
  const textarea = inputRef.value?.$el?.querySelector('textarea')
  if (textarea) {
    textarea.focus()
  }
}

defineExpose({
  focus
})
</script>

<style scoped>
.chat-input {
  display: flex;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: white;
}

.chat-input :deep(.el-textarea) {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 24px;
  padding: 12px 16px;
  font-size: 14px;
  resize: none;
}

.chat-input :deep(.el-textarea__inner):focus {
  border-color: #667eea;
}

.chat-input :deep(.el-button) {
  border-radius: 24px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 500;
  height: auto;
  align-self: flex-end;
}

.chat-input :deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.chat-input :deep(.el-button--primary:hover) {
  opacity: 0.9;
}

.chat-input :deep(.el-button--danger) {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
  border: none;
}

.chat-input :deep(.el-button--danger:hover) {
  opacity: 0.9;
}

.chat-input :deep(.el-button.is-disabled) {
  opacity: 0.5;
}
</style>
