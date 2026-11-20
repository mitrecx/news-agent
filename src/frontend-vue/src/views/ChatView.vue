<template>
  <div class="chat-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">A LITTLE MORE CONTEXT</span>
        <h1>智能对话<span class="heading-dot">.</span></h1>
        <p>聊聊正在发生的事，或让 AI 为你整理思路。</p>
      </div>
      <RouterLink to="/settings" class="chat-model"
        ><el-icon><Cpu /></el-icon>{{ settings.model?.name || '未选择模型'
        }}<el-icon><ArrowDown /></el-icon
      ></RouterLink>
    </div>
    <div v-if="!settings.model" class="model-setup-notice">
      <el-icon><Cpu /></el-icon>添加并启用一个模型后，即可开始对话。<RouterLink to="/settings"
        >配置模型 →</RouterLink
      >
    </div>
    <div class="chat-workspace surface">
      <ConversationSidebar
        :busy="chat.isStreaming"
        @select="selectConversation"
        @new="newConversation"
      />
      <section class="chat-main">
        <header class="conversation-heading">
          <span class="status-dot" /><strong>{{ conversationTitle }}</strong
          ><span>仅你可见</span>
        </header>
        <div ref="messagesContainer" class="chat-scroll" aria-live="polite">
          <div v-if="!chat.messages.length" class="chat-welcome">
            <span class="welcome-symbol">n<span>.</span></span
            ><span class="eyebrow">NEWS, WITH CONTEXT.</span>
            <h2>世界很热闹，<br />我们一起理清头绪。</h2>
            <p>了解最新热点，或从一个简单的问题开始。</p>
            <div class="conversation-starters">
              <button
                v-for="prompt in starters"
                :key="prompt.title"
                @click="sendMessage(prompt.question)"
              >
                <span>{{ prompt.title }}</span
                ><span>↗</span><small>{{ prompt.subtitle }}</small>
              </button>
            </div>
          </div>
          <div v-else class="message-list">
            <ChatMessage
              v-for="(item, index) in chat.messages"
              :key="index"
              :message="item"
              :is-streaming="
                chat.isStreaming && index === chat.messages.length - 1 && item.role === 'assistant'
              "
            />
          </div>
          <div v-if="progressMessage" class="chat-progress">
            <el-icon class="is-loading"><Loading /></el-icon>{{ progressMessage }}
          </div>
        </div>
        <ChatInput
          ref="input"
          :is-streaming="chat.isStreaming"
          :is-connected="chat.isConnected"
          :messages="chat.messages"
          @send="sendMessage"
          @stop="stopStreaming"
        />
        <p class="chat-disclaimer">AI 的回答可能不准确，重要信息请核实来源。</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cpu, ArrowDown, Loading } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useSettingsStore } from '@/stores/settings'
import { useChatStream } from '@/composables/useChatStream'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import ChatInput from '@/components/ChatInput.vue'
import ChatMessage from '@/components/ChatMessage.vue'
const chat = useChatStore()
const conversations = useConversationStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()
const { sendMessage, progressMessage, stopStreaming, loadConversation, startNewConversation } =
  useChatStream()
const messagesContainer = ref<HTMLElement>()
const input = ref<InstanceType<typeof ChatInput>>()
const conversationTitle = computed(() => conversations.currentConversation?.title || '新的对话')
const starters = [
  {
    title: '现在大家在关注什么？',
    subtitle: '获取最新微博热搜',
    question: '帮我看看现在的微博热搜。',
  },
  {
    title: '让信息更容易理解',
    subtitle: '提炼重点，整理思路',
    question: '请告诉我如何从新闻中提炼事实、观点和待核实的信息。',
  },
]
const newConversation = () => {
  stopStreaming()
  startNewConversation()
  nextTick(() => input.value?.focus())
}
const selectConversation = async (id: number) => {
  stopStreaming()
  await loadConversation(id)
}
watch(
  () => chat.messages.map((item) => item.content).join(''),
  async () => {
    await nextTick()
    const container = messagesContainer.value
    if (container) container.scrollTop = container.scrollHeight
  },
)
onMounted(async () => {
  await conversations.fetchConversations()
  const topic = typeof route.query.topic === 'string' ? route.query.topic : null
  if (topic) {
    startNewConversation()
    input.value?.setDraft(`请帮我了解一下「${topic}」。`)
    router.replace('/chat')
  } else if (
    conversations.currentConversationId &&
    conversations.conversations.some((item) => item.id === conversations.currentConversationId)
  )
    await loadConversation(conversations.currentConversationId)
  else {
    startNewConversation()
  }
  await nextTick()
  input.value?.focus()
})
</script>

<style scoped>
.model-setup-notice {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 18px;
  border: 1px solid #dbe7e2;
  border-radius: 8px;
  background: #f0f6f3;
  font-size: 12px;
  color: #65857a;
}
.model-setup-notice a {
  margin-left: auto;
  color: #337668;
  white-space: nowrap;
}
.heading-dot {
  color: #58a28f;
}
.chat-model {
  display: flex;
  gap: 9px;
  align-items: center;
  color: #708b88;
  border: 1px solid #dce8e3;
  background: #f0f6f3;
  padding: 10px 13px;
  border-radius: 8px;
  font-size: 10px;
}
.chat-model .el-icon:last-child {
  margin-left: 8px;
  font-size: 9px;
}
.chat-workspace {
  position: relative;
  display: flex;
  height: calc(100dvh - 233px);
  min-height: 530px;
  overflow: hidden;
}
.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.conversation-heading {
  height: 57px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 25px;
  border-bottom: 1px solid #eff3f4;
}
.conversation-heading strong {
  font-size: 11px;
  font-weight: 500;
  max-width: 75%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.conversation-heading > span:last-child {
  margin-left: auto;
  font-size: 9px;
  color: #b1bdc2;
}
.conversation-heading .status-dot {
  width: 5px;
  height: 5px;
}
.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 26px 32px;
}
.chat-welcome {
  min-height: 100%;
  display: flex;
  justify-content: center;
  flex-direction: column;
  max-width: 480px;
  margin: auto;
  padding: 22px 0 34px;
}
.welcome-symbol {
  font:
    700 54px Georgia,
    serif;
  color: #35796a;
  letter-spacing: -4px;
  margin-bottom: 26px;
}
.welcome-symbol > span {
  color: #b4d3ba;
}
.chat-welcome > .eyebrow {
  font-size: 8px;
  color: #9badaf;
  letter-spacing: 2px;
}
.chat-welcome h2 {
  font-size: 28px;
  line-height: 1.65;
  font-weight: 500;
  letter-spacing: -0.9px;
  margin: 7px 0 13px;
  color: #536e74;
}
.chat-welcome > p {
  color: #a5b1b8;
  font-size: 11px;
}
.conversation-starters {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 33px;
}
.conversation-starters button {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 9px;
  text-align: left;
  border: 1px solid #e5ecea;
  background: #fbfdfc;
  border-radius: 9px;
  padding: 17px 15px;
  color: #6f8c82;
  font-size: 10px;
}
.conversation-starters button:hover {
  background: #eff6f2;
  border-color: #c7ded2;
}
.conversation-starters small {
  color: #a7b6b7;
  font-size: 9px;
  grid-column: 1 / -1;
}
.message-list {
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-width: 760px;
  margin: auto;
}
.chat-disclaimer {
  flex-shrink: 0;
  font-size: 8px;
  color: #b3bec5;
  text-align: center;
  padding: 12px 20px 18px;
}
.chat-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 10px;
  color: #9aaeb1;
  padding: 22px;
}
@media (max-width: 1050px) {
  .chat-scroll {
    padding: 24px;
  }
  .chat-welcome h2 {
    font-size: 24px;
  }
  .conversation-starters {
    grid-template-columns: 1fr;
  }
  .chat-workspace {
    min-height: 600px;
  }
}
@media (max-width: 760px) {
  .chat-workspace {
    height: calc(100dvh - 235px);
    min-height: 540px;
  }
  .chat-model {
    font-size: 9px;
  }
  .chat-scroll {
    padding: 22px 17px;
  }
  .conversation-heading {
    padding: 0 17px;
  }
  .chat-welcome h2 {
    font-size: 22px;
  }
  .welcome-symbol {
    font-size: 44px;
  }
  .chat-disclaimer {
    font-size: 8px;
  }
}
</style>
