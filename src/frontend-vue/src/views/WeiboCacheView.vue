<template>
  <div class="weibo-cache-view">
    <div class="top-nav">
      <div class="nav-content">
        <el-button link @click="router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <div class="user-menu">
          <el-dropdown trigger="click">
            <div class="user-dropdown">
              <div class="user-avatar">{{ authStore.user?.username?.charAt(0).toUpperCase() || '?' }}</div>
              <span>{{ authStore.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/chat')">
                  <el-icon><ChatDotRound /></el-icon>
                  智能对话
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/hot-search')">
                  <el-icon><TrendCharts /></el-icon>
                  热搜查询
                </el-dropdown-item>
                <el-dropdown-item @click="handleLogout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <div class="cache-header">
      <h1>微博热搜缓存</h1>
      <el-button @click="refreshCache" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 统计信息 -->
    <div class="stats-section">
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.total_entries || 0 }}</div>
          <div class="stat-label">总条目</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.active_entries || 0 }}</div>
          <div class="stat-label">活跃条目</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.from_weibo || 0 }}</div>
          <div class="stat-label">来自微博</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.from_llm || 0 }}</div>
          <div class="stat-label">来自LLM</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.created_last_hour || 0 }}</div>
          <div class="stat-label">近1小时创建</div>
        </div>
      </el-card>
    </div>

    <!-- 搜索和过滤 -->
    <div class="search-section">
      <el-input
        v-model="searchQuery"
        placeholder="搜索热搜标题..."
        @input="handleSearch"
        clearable
        style="width: 300px"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button @click="handleDeleteExpired" type="danger" plain>
        <el-icon><Delete /></el-icon>
        删除过期缓存
      </el-button>
    </div>

    <!-- 缓存列表 -->
    <el-table :data="cacheItems" stripe v-loading="loading" class="cache-table">
      <el-table-column prop="title" label="热搜标题" min-width="200">
        <template #default="{ row }">
          <div class="title-cell">{{ row.title }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="300">
        <template #default="{ row }">
          <div class="description-cell">{{ row.description || '-' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="description_source" label="来源" width="120">
        <template #default="{ row }">
          <el-tag :type="getSourceTagType(row.description_source)">
            {{ getSourceLabel(row.description_source) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="expires_at" label="过期时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.expires_at) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-section">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, Delete, ArrowLeft, ArrowDown, ChatDotRound, SwitchButton, TrendCharts } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getWeiboCache, getWeiboCacheStats, deleteExpiredCache, type WeiboCacheItem, type WeiboCacheStats } from '@/api/weibo'

const router = useRouter()
const authStore = useAuthStore()

// 数据
const cacheItems = ref<WeiboCacheItem[]>([])
const stats = ref<WeiboCacheStats>({
  total_entries: 0,
  active_entries: 0,
  expired_entries: 0,
  created_last_hour: 0,
  from_weibo: 0,
  from_llm: 0,
  from_fallback: 0,
})
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

// 获取缓存列表
const fetchCache = async () => {
  loading.value = true
  try {
    const response = await getWeiboCache({
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
      search: searchQuery.value || undefined,
    })
    cacheItems.value = response.data.items
    total.value = response.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '获取缓存列表失败')
  } finally {
    loading.value = false
  }
}

// 获取统计信息
const fetchStats = async () => {
  try {
    const response = await getWeiboCacheStats()
    stats.value = response.data
  } catch (error: any) {
    console.error('获取统计信息失败:', error)
  }
}

// 刷新缓存
const refreshCache = () => {
  fetchCache()
  fetchStats()
}

// 搜索处理
let searchTimer: ReturnType<typeof setTimeout>
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchCache()
  }, 500)
}

// 分页处理
const handlePageChange = () => {
  fetchCache()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchCache()
}

// 删除过期缓存
const handleDeleteExpired = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除所有过期的缓存条目吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await deleteExpiredCache()
    ElMessage.success(response.data.message || '删除成功')
    refreshCache()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 格式化日期时间
const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 获取来源标签类型
const getSourceTagType = (source: string) => {
  switch (source) {
    case 'weibo_detail':
      return 'success'
    case 'llm':
      return 'warning'
    case 'fallback':
      return 'info'
    default:
      return ''
  }
}

// 获取来源标签文本
const getSourceLabel = (source: string) => {
  switch (source) {
    case 'weibo_detail':
      return '微博详情'
    case 'llm':
      return 'LLM推理'
    case 'fallback':
      return '后备'
    default:
      return source
  }
}

// 初始化
onMounted(() => {
  fetchCache()
  fetchStats()
})

// 退出登录
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}
</script>

<style scoped>
.weibo-cache-view {
  min-height: 100vh;
  background: #f5f7fa;
}

.top-nav {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1600px;
  margin: 0 auto;
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

.weibo-cache-view {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.cache-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.cache-header h1 {
  font-size: 28px;
  margin: 0;
  font-weight: 600;
  color: #303133;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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

.stat-label {
  font-size: 14px;
  color: #909399;
}

.search-section {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.cache-table {
  margin-bottom: 16px;
}

.title-cell {
  font-weight: 500;
  color: #303133;
}

.description-cell {
  color: #606266;
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.pagination-section {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
