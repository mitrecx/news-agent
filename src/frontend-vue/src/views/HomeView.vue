<template>
  <div class="home-view">
    <!-- 顶部导航栏 -->
    <AppNav :full-width="true" />

    <!-- 首页内容 -->
    <div class="home-container">
      <!-- Welcome Section -->
      <div class="welcome-section">
        <div class="welcome-content">
          <h1 class="welcome-title">欢迎使用 News Agent</h1>
          <p class="welcome-subtitle">基于 DeepSeek 模型的智能对话助手，支持查询微博热搜</p>
        </div>
      </div>

      <!-- Navigation Cards -->
      <div class="navigation-cards">
        <el-card class="nav-card chat-card" shadow="hover" @click="navigateToChat">
          <div class="card-content">
            <div class="card-icon chat-icon">
              <el-icon :size="48"><ChatDotRound /></el-icon>
            </div>
            <h2 class="card-title">智能对话</h2>
            <p class="card-description">与 AI 助手进行实时对话，获取新闻资讯和智能问答</p>
            <div class="card-features">
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                实时对话
              </span>
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                对话历史
              </span>
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                智能回复
              </span>
            </div>
          </div>
        </el-card>

        <el-card class="nav-card hotsearch-card" shadow="hover" @click="navigateToHotSearch">
          <div class="card-content">
            <div class="card-icon hotsearch-icon">
              <el-icon :size="48"><TrendCharts /></el-icon>
            </div>
            <h2 class="card-title">微博热搜</h2>
            <p class="card-description">查看实时微博热搜榜单，了解最新热点资讯</p>
            <div class="card-features">
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                实时榜单
              </span>
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                热度排序
              </span>
              <span class="feature-tag">
                <el-icon><Check /></el-icon>
                直接查询
              </span>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElCard, ElIcon } from 'element-plus'
import { ChatDotRound, TrendCharts, Check } from '@element-plus/icons-vue'
import AppNav from '@/components/AppNav.vue'

const router = useRouter()

const navigateToChat = () => {
  router.push('/chat')
}

const navigateToHotSearch = () => {
  router.push('/hot-search')
}
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
}

.home-container {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 40px;
  margin: 20px;
  max-width: 1200px;
  width: calc(100% - 40px);
}

.welcome-section {
  text-align: center;
  margin-bottom: 60px;
  color: white;
}

.welcome-content {
  animation: fadeInUp 0.8s ease-out;
}

.welcome-title {
  font-size: 48px;
  font-weight: 700;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.welcome-subtitle {
  font-size: 18px;
  margin: 0;
  opacity: 0.9;
  font-weight: 300;
}

.navigation-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 32px;
  animation: fadeInUp 0.8s ease-out 0.2s backwards;
}

.nav-card {
  cursor: pointer;
  border-radius: 20px;
  overflow: hidden;
  transition: all 0.3s ease;
  background: white;
  border: none;
}

.nav-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.card-content {
  padding: 40px;
  text-align: center;
}

.card-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.chat-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.hotsearch-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.card-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #1f2937;
}

.card-description {
  font-size: 16px;
  color: #6b7280;
  margin: 0 0 24px 0;
  line-height: 1.6;
}

.card-features {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #f3f4f6;
  border-radius: 20px;
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.feature-tag .el-icon {
  font-size: 14px;
  color: #10b981;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .home-container {
    padding: 40px 24px;
    margin: 16px;
    width: calc(100% - 32px);
  }

  .welcome-title {
    font-size: 32px;
  }

  .welcome-subtitle {
    font-size: 16px;
  }

  .navigation-cards {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .card-content {
    padding: 32px 24px;
  }

  .card-title {
    font-size: 24px;
  }

  .card-description {
    font-size: 14px;
  }
}
</style>
