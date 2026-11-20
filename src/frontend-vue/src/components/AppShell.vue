<template>
  <div class="workspace">
    <aside class="workspace-sidebar">
      <RouterLink to="/" class="brand" aria-label="News Agent 首页"
        ><span class="brand-mark">n<span>.</span></span
        ><span class="brand-name">News Agent<small>你的新闻工作台</small></span></RouterLink
      >
      <span class="nav-label">工作空间</span>
      <nav aria-label="主导航" class="main-nav">
        <RouterLink
          to="/"
          aria-label="热点资讯"
          title="热点资讯"
          class="nav-item"
          :class="{ selected: route.path === '/' }"
          ><el-icon><TrendCharts /></el-icon><span>热点资讯</span
          ><span class="nav-arrow">↗</span></RouterLink
        >
        <RouterLink
          to="/chat"
          aria-label="智能对话"
          title="智能对话"
          class="nav-item"
          :class="{ selected: route.path === '/chat' }"
          ><el-icon><ChatLineRound /></el-icon><span>智能对话</span></RouterLink
        >
      </nav>
      <span class="nav-label settings-nav-label">偏好与连接</span>
      <nav aria-label="设置导航" class="main-nav">
        <RouterLink
          to="/settings"
          aria-label="设置"
          title="设置"
          class="nav-item"
          :class="{ selected: route.path.startsWith('/settings') }"
          ><el-icon><Setting /></el-icon><span>设置</span></RouterLink
        >
      </nav>
      <div class="sidebar-bottom">
        <RouterLink to="/settings" class="model-indicator"
          ><span class="status-dot" :class="{ muted: !settings.model?.has_api_key }"></span
          ><span
            ><small>当前模型</small
            ><strong>{{ settings.model?.name || '未选择模型' }}</strong></span
          ><el-icon><ArrowRight /></el-icon
        ></RouterLink>
        <div class="sidebar-user">
          <span class="user-initial">{{
            auth.user?.username?.slice(0, 1).toUpperCase() || 'U'
          }}</span
          ><span
            ><strong>{{ auth.user?.username || '用户' }}</strong
            ><small>个人工作空间</small></span
          ><button class="icon-button" aria-label="退出登录" title="退出登录" @click="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </div>
      </div>
    </aside>
    <section class="workspace-main" :class="{ 'workspace-main-news': route.path === '/' }">
      <header class="workspace-topbar">
        <span class="breadcrumb"
          >工作空间 <span>/</span> <strong>{{ pageName }}</strong></span
        >
        <div class="topbar-meta">
          <span class="today-label">{{ today }}</span
          ><span class="service-state"
            ><i class="status-dot" :class="{ muted: !chat.isConnected }"></i
            >{{ chat.isConnected ? '服务已连接' : '连接中' }}</span
          >
        </div>
      </header>
      <main
        class="workspace-page"
        :class="{
          'workspace-page-chat': route.path === '/chat',
          'workspace-page-news': route.path === '/',
        }"
      >
        <RouterView />
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  TrendCharts,
  ChatLineRound,
  Setting,
  ArrowRight,
  SwitchButton,
} from '@element-plus/icons-vue'
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
const pageName = computed(() =>
  route.path === '/chat' ? '智能对话' : route.path.startsWith('/settings') ? '设置' : '热点资讯',
)
const today = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())
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
