<template>
  <div class="chat-input">
    <el-input
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
import { ref } from 'vue'
import { ElInput, ElButton } from 'element-plus'

const props = defineProps<{
  isStreaming: boolean
  isConnected: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const inputMessage = ref('')

const handleSend = () => {
  const message = inputMessage.value.trim()
  if (!message || props.isStreaming || !props.isConnected) return

  emit('send', message)
  inputMessage.value = ''
}

const handleKeydown = (event: Event | KeyboardEvent) => {
  if (event instanceof KeyboardEvent && event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

const handleInput = () => {
  // Auto-resize handled by el-input autosize prop
}
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
