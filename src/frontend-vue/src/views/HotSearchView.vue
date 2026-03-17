<template>
  <div class="hot-search-view">
    <div class="page-header">
      <div class="header-content">
        <h1>微博热搜</h1>
        <p class="subtitle">实时微博热搜数据（直接查询，不经过大模型处理）</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="fetchHotSearch" :loading="loading" :icon="Refresh">
          刷新数据
        </el-button>
        <el-select v-model="limit" @change="handleLimitChange" style="width: 120px; margin-left: 12px">
          <el-option label="20 条" :value="20" />
          <el-option label="50 条" :value="50" />
          <el-option label="100 条" :value="100" />
        </el-select>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section">
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ totalItems }}</div>
          <div class="stat-label">热搜条数</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value" :class="{ 'status-active': !loading, 'status-loading': loading }">
            {{ loading ? '加载中' : '实时数据' }}
          </div>
          <div class="stat-label">数据状态</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ lastUpdateTime }}</div>
          <div class="stat-label">最后更新</div>
        </div>
      </el-card>
    </div>

    <!-- 热搜列表 -->
    <div class="hot-search-list">
      <el-empty v-if="!loading && hotSearchItems.length === 0" description="暂无热搜数据" />

      <transition-group name="list" tag="div" class="items-container">
        <el-card
          v-for="item in hotSearchItems"
          :key="item.rank"
          class="hot-search-card"
          :class="`rank-${item.rank <= 3 ? item.rank : 'normal'}`"
          shadow="hover"
        >
          <div class="card-content">
            <div class="rank-badge" :class="`rank-${item.rank <= 3 ? item.rank : 'normal'}`">
              {{ item.rank }}
            </div>
            <div class="item-content">
              <h3 class="item-title">{{ item.title }}</h3>
              <p v-if="item.description" class="item-description">
                {{ item.description }}
              </p>
            </div>
          </div>
        </el-card>
      </transition-group>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-section">
      <el-skeleton :rows="5" animated />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getWeiboHotSearch, type HotSearchItem } from '@/api/hotsearch'

// 数据
const hotSearchItems = ref<HotSearchItem[]>([])
const loading = ref(false)
const limit = ref(50)
const totalItems = ref(0)
const lastUpdateTime = ref('-')

// 获取热搜数据
const fetchHotSearch = async () => {
  loading.value = true
  try {
    const response = await getWeiboHotSearch({ limit: limit.value })
    hotSearchItems.value = response.data.items
    totalItems.value = response.data.total

    // 更新时间
    const now = new Date()
    lastUpdateTime.value = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

    ElMessage.success(`成功获取 ${totalItems.value} 条热搜数据`)
  } catch (error: any) {
    ElMessage.error(error.message || '获取热搜数据失败')
    console.error('获取热搜数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理限制数量变化
const handleLimitChange = () => {
  fetchHotSearch()
}

// 初始化
onMounted(() => {
  fetchHotSearch()
})
</script>

<style scoped>
.hot-search-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-content h1 {
  font-size: 28px;
  margin: 0 0 8px 0;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.header-actions {
  display: flex;
  align-items: center;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.stat-item {
  padding: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 8px;
}

.stat-value.status-active {
  color: #67c23a;
}

.stat-value.status-loading {
  color: #909399;
  font-size: 24px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.hot-search-list {
  min-height: 200px;
}

.items-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hot-search-card {
  transition: all 0.3s ease;
}

.hot-search-card.rank-1 {
  border-left: 4px solid #f56c6c;
  background: linear-gradient(to right, #fef0f0, #ffffff);
}

.hot-search-card.rank-2 {
  border-left: 4px solid #e6a23c;
  background: linear-gradient(to right, #fdf6ec, #ffffff);
}

.hot-search-card.rank-3 {
  border-left: 4px solid #409eff;
  background: linear-gradient(to right, #ecf5ff, #ffffff);
}

.card-content {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.rank-badge {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  background: #909399;
}

.rank-badge.rank-1 {
  background: linear-gradient(135deg, #f56c6c, #ff8787);
}

.rank-badge.rank-2 {
  background: linear-gradient(135deg, #e6a23c, #f0b857);
}

.rank-badge.rank-3 {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.rank-badge.rank-normal {
  background: #909399;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  line-height: 1.5;
}

.item-description {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.loading-section {
  padding: 20px 0;
}

/* 列表动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateY(-30px);
}

.list-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }

  .card-content {
    gap: 12px;
  }

  .rank-badge {
    width: 32px;
    height: 32px;
    font-size: 14px;
  }

  .item-title {
    font-size: 16px;
  }

  .item-description {
    font-size: 13px;
  }
}
</style>
