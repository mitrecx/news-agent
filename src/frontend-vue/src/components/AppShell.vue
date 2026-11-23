<template>
  <div class="workspace">
    <header class="workspace-header">
      <div class="workspace-header-inner">
        <RouterLink to="/" class="workspace-brand" aria-label="News Agent 首页">
          <el-icon><DocumentCopy /></el-icon><span>News Agent</span>
        </RouterLink>
        <nav class="workspace-nav" aria-label="主导航">
          <RouterLink to="/" :class="{ selected: isNews }" :aria-current="isNews ? 'page' : undefined">
            热点资讯
          </RouterLink>
          <RouterLink to="/chat" :class="{ selected: route.path === '/chat' }">
            智能对话
          </RouterLink>
        </nav>
        <div class="workspace-account">
          <RouterLink to="/settings" class="workspace-settings" :class="{ selected: route.path === '/settings' }">
            <el-icon><Setting /></el-icon><span>设置</span>
          </RouterLink>
          <span class="workspace-username">{{ auth.user?.username || '用户' }}</span>
          <button class="icon-button" aria-label="退出登录" title="退出登录" @click="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </div>
      </div>
    </header>
    <main class="workspace-page" :class="{ 'workspace-page-chat': route.path === '/chat' }">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DocumentCopy, Setting, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useConversationStore } from '@/stores/conversation'
import { useSettingsStore } from '@/stores/settings'
import { useHealthCheck } from '@/composables/useHealthCheck'
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const conversations = useConversationStore()
const settings = useSettingsStore()
const isNews = computed(() => route.path === '/' || route.path.startsWith('/news/'))
useHealthCheck()
onMounted(() => settings.refresh())
const logout = () => {
  auth.logout()
  chat.clearMessages()
  chat.setConversationId(null)
  conversations.conversations = []
  conversations.clearCurrentConversation()
  settings.clear()
  router.push('/login')
}
</script>
