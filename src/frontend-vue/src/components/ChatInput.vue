<template>
  <div class="composer">
    <div class="composer-box">
      <el-input
        ref="input"
        v-model="draft"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        :disabled="isStreaming || !isConnected"
        placeholder="有什么想了解的，问问我…"
        aria-label="聊天消息"
        @keydown="handleKeydown"
      />
      <div class="composer-footer">
        <span
          ><el-icon><MagicStick /></el-icon
          >{{ isConnected ? '从问题出发，获得更多理解' : '正在连接服务…' }}</span
        ><button
          v-if="isStreaming"
          class="send-button stop-button"
          aria-label="停止生成"
          @click="$emit('stop')"
        >
          <el-icon><VideoPause /></el-icon></button
        ><button
          v-else
          class="send-button"
          aria-label="发送消息"
          :disabled="!draft.trim() || !isConnected"
          @click="send"
        >
          <el-icon><Top /></el-icon>
        </button>
      </div>
    </div>
    <div class="composer-hint">Enter 发送 <span>·</span> Shift + Enter 换行</div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElInput } from 'element-plus'
import { MagicStick, Top, VideoPause } from '@element-plus/icons-vue'
import type { ChatMessage } from '@/types'
const props = defineProps<{
  isStreaming: boolean
  isConnected: boolean
  messages: ChatMessage[]
}>()
const emit = defineEmits<{ send: [value: string]; stop: [] }>()
const draft = ref('')
const input = ref<InstanceType<typeof ElInput>>()
const send = () => {
  if (!draft.value.trim() || props.isStreaming || !props.isConnected) return
  emit('send', draft.value.trim())
  draft.value = ''
}
const handleKeydown = (event: Event | KeyboardEvent) => {
  if (
    event instanceof KeyboardEvent &&
    event.key === 'Enter' &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault()
    send()
  }
}
defineExpose({
  focus: () => input.value?.focus(),
  setDraft: (value: string) => {
    draft.value = value
  },
})
</script>
<style scoped>
.composer {
  flex-shrink: 0;
  padding: 0 30px;
}
.composer-box {
  border: 1px solid #dce7e3;
  box-shadow: 0 3px 14px #325b4204;
  border-radius: 11px;
  padding: 13px 15px 10px;
  background: #fff;
}
.composer-box:focus-within {
  border-color: #93b6a6;
}
.composer :deep(.el-textarea__inner) {
  resize: none;
  box-shadow: none;
  padding: 0;
  background: transparent;
  color: #57706f;
  font-size: 12px;
  line-height: 1.8;
}
.composer :deep(.el-textarea__inner::placeholder) {
  color: #abb8bd;
}
.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}
.composer-footer > span {
  color: #a5b9b0;
  font-size: 9px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.send-button {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #3f8570;
  color: #fff;
  border: none;
  font-size: 17px;
}
.send-button:disabled {
  background: #e6efea;
  color: #b1c8bd;
}
.stop-button {
  background: #8ca69b;
}
.composer-hint {
  display: flex;
  justify-content: flex-end;
  gap: 7px;
  color: #b6c1c6;
  font-size: 8px;
  margin-top: 8px;
}
.composer-hint span {
  color: #ccd3d8;
}
@media (max-width: 760px) {
  .composer {
    padding: 0 15px;
  }
  .composer-footer > span {
    font-size: 8px;
  }
  .composer-box {
    padding: 12px;
  }
}
</style>
