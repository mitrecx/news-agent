<template>
  <div :class="['chat-message', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '你' : 'AI' }}
    </div>
    <div class="bubble">
      <div
        v-if="message.role === 'assistant'"
        class="markdown-content"
        v-html="renderedContent"
      ></div>
      <div v-else class="text-content">{{ message.content }}</div>
      <span v-if="isStreaming" class="cursor"></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { ChatMessage } from '@/types'

const props = defineProps<{
  message: ChatMessage
  isStreaming?: boolean
}>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return md.render(props.message.content)
  }
  return props.message.content
})
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 11px;
  width: 100%;
  font-size: 12px;
}
.avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  background: #eaf3ed;
  color: #6b9b86;
  border-radius: 9px;
  font-size: 9px;
}
.user {
  flex-direction: row-reverse;
}
.user .avatar {
  background: #f0e9e0;
  color: #b29675;
}
.bubble {
  min-width: 0;
  max-width: calc(100% - 45px);
  line-height: 2;
  overflow-wrap: anywhere;
  color: #6e838b;
}
.user .bubble {
  padding: 10px 15px;
  background: #f0f5f2;
  border-radius: 10px 0 10px 10px;
  color: #658476;
}
.markdown-content :deep(p) {
  margin: 0 0 10px;
}
.markdown-content :deep(p:last-child) {
  margin: 0;
}
.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin: 10px 0;
}
.markdown-content :deep(pre) {
  overflow-x: auto;
  background: #f4f7f8;
  padding: 15px;
  border-radius: 8px;
  font:
    11px Menlo,
    monospace;
  line-height: 1.7;
  margin: 12px 0;
}
.markdown-content :deep(code) {
  background: #f0f4f5;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 11px;
}
.markdown-content :deep(table) {
  border-collapse: collapse;
  display: block;
  overflow-x: auto;
}
.markdown-content :deep(td),
.markdown-content :deep(th) {
  padding: 8px;
  border: 1px solid #e0e8eb;
}
.markdown-content :deep(a) {
  color: #3f8e77;
  text-decoration: underline;
}
.cursor {
  width: 3px;
  height: 12px;
  background: #84ae9b;
  display: inline-block;
  margin-left: 4px;
  animation: blink 1s infinite;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
</style>
