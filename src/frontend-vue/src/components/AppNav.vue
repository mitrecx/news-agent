<template>
  <div class="app-nav" :class="{ 'app-nav--transparent': transparent, 'app-nav--full-width': fullWidth }">
    <div class="nav-content">
      <!-- Navigation Tabs -->
      <div class="nav-tabs">
        <div
          class="nav-tab"
          :class="{ 'nav-tab--active': activeRoute === '/' || activeRoute === '/hot-search' }"
          @click="navigateTo('/')"
        >
          <el-icon><TrendCharts /></el-icon>
          热搜查询
        </div>
        <div
          class="nav-tab"
          :class="{ 'nav-tab--active': activeRoute === '/chat' }"
          @click="navigateTo('/chat')"
        >
          <el-icon><ChatDotRound /></el-icon>
          智能对话
        </div>
        <div
          class="nav-tab"
          :class="{ 'nav-tab--active': activeRoute === '/weibo-login' }"
          @click="navigateTo('/weibo-login')"
        >
          <el-icon><Key /></el-icon>
          微博登录
        </div>
      </div>

      <!-- User Dropdown -->
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-dropdown">
          <div class="user-avatar">{{ authStore.user?.username?.charAt(0).toUpperCase() || '?' }}</div>
          <span>{{ authStore.user?.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElIcon, ElDropdown, ElDropdownMenu, ElDropdownItem } from 'element-plus'
import { ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

interface Props {
  transparent?: boolean
  fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  transparent: false,
  fullWidth: false,
})

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeRoute = computed(() => route.path)

const navigateTo = (path: string) => {
  router.push(path)
}

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-nav {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
}

.app-nav--transparent {
  background: rgba(255, 255, 255, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 24px;
}

.app-nav--full-width .nav-content {
  max-width: 1600px;
  padding: 12px 24px;
}

.nav-tabs {
  display: flex;
  gap: 12px;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #f3f4f6;
  border-radius: 8px;
  transition: all 0.2s;
  color: #374151;
  cursor: pointer;
  font-weight: 500;
}

.nav-tab:hover {
  background: #e5e7eb;
}

.app-nav--transparent .nav-tab {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.app-nav--transparent .nav-tab:hover {
  background: rgba(255, 255, 255, 0.3);
}

.nav-tab--active,
.nav-tab--active.app-nav--transparent .nav-tab {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.nav-tab--active:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background 0.2s;
  color: #374151;
}

.user-dropdown:hover {
  background: #f3f4f6;
}

.app-nav--transparent .user-dropdown {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.app-nav--transparent .user-dropdown:hover {
  background: rgba(255, 255, 255, 0.3);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.app-nav--transparent .user-avatar {
  background: rgba(255, 255, 255, 0.3);
}

/* Responsive */
@media (max-width: 768px) {
  .nav-tabs {
    gap: 8px;
  }

  .nav-tab {
    padding: 8px 12px;
    font-size: 14px;
  }

  .nav-tab span:not(.el-icon) {
    display: none;
  }

  .user-dropdown span:not(.user-avatar):not(.el-icon) {
    display: none;
  }
}
</style>
