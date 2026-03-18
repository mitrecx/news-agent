<template>
  <div class="hot-search-view">
    <div class="top-nav">
      <div class="nav-content">
        <div class="nav-tabs">
          <div class="nav-tab" @click="router.push('/')">
            <el-icon><HomeFilled /></el-icon>
            首页
          </div>
          <div class="nav-tab" @click="router.push('/chat')">
            <el-icon><ChatDotRound /></el-icon>
            智能对话
          </div>
          <div class="nav-tab active">
            <el-icon><TrendCharts /></el-icon>
            热搜查询
          </div>
        </div>
        <el-dropdown trigger="click">
          <div class="user-dropdown">
            <div class="user-avatar">{{ authStore.user?.username?.charAt(0).toUpperCase() || '?' }}</div>
            <span>{{ authStore.user?.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout" divided>
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <template #header>
        <el-form :inline="true" :model="filters" class="filter-form">
          <el-form-item label="标题搜索">
            <el-input
              v-model="filters.search"
              placeholder="输入关键词搜索标题"
              clearable
              style="width: 240px"
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="更新时间">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD HH:mm:ss"
              @change="handleDateRangeChange"
              style="width: 320px"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleSearch" :icon="Search">
              查询
            </el-button>
            <el-button @click="handleReset" :icon="RefreshLeft">
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <el-table
        :data="cacheItems"
        v-loading="loading"
        stripe
        class="hot-search-table"
        :default-sort="{ prop: 'updated_at', order: 'descending' }"
      >
        <el-table-column type="index" label="#" width="60" :index="indexMethod" />

        <el-table-column prop="title" label="热搜标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="title-cell">
              <el-tag v-if="row.description_source === 'weibo_detail'" size="small" type="success" style="margin-right: 8px">
                微博
              </el-tag>
              <el-tag v-else-if="row.description_source === 'llm'" size="small" type="warning" style="margin-right: 8px">
                AI
              </el-tag>
              <el-tag v-else size="small" type="info" style="margin-right: 8px">
                其他
              </el-tag>
              {{ row.title }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip popper-class="description-tooltip">
          <template #default="{ row }">
            <span class="description-cell">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column prop="updated_at" label="更新时间" width="180" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-section">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[15, 30, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, RefreshLeft, ArrowDown, ChatDotRound, SwitchButton, TrendCharts, HomeFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getWeiboHotSearchCache, type HotSearchCacheItem } from '@/api/hotsearch'

const router = useRouter()
const authStore = useAuthStore()

// 数据
const cacheItems = ref<HotSearchCacheItem[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)

// 过滤条件
const filters = ref({
  search: '',
  start_date: undefined as string | undefined,
  end_date: undefined as string | undefined,
})
const dateRange = ref<[string, string] | null>(null)

// 索引方法
const indexMethod = (index: number) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
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

// 获取缓存数据
const fetchCache = async () => {
  loading.value = true
  try {
    const response = await getWeiboHotSearchCache({
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
      search: filters.value.search || undefined,
      start_date: filters.value.start_date,
      end_date: filters.value.end_date,
    })
    cacheItems.value = response.data.items
    total.value = response.data.total

    if (response.data.items.length === 0) {
      ElMessage.info('未找到匹配的数据')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取热搜数据失败')
    console.error('获取热搜数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchCache()
}

// 处理重置
const handleReset = () => {
  filters.value = {
    search: '',
    start_date: undefined,
    end_date: undefined,
  }
  dateRange.value = null
  currentPage.value = 1
  fetchCache()
}

// 处理日期范围变化
const handleDateRangeChange = (value: [string, string] | null) => {
  if (value && value.length === 2) {
    filters.value.start_date = value[0]
    filters.value.end_date = value[1]
  } else {
    filters.value.start_date = undefined
    filters.value.end_date = undefined
  }
}

// 处理分页变化
const handlePageChange = () => {
  fetchCache()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchCache()
}

// 退出登录
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}

// 初始化
onMounted(() => {
  // 设置默认日期范围为今天
  const today = new Date()
  const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0)
  const endOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59)

  const formatDate = (date: Date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }

  dateRange.value = [formatDate(startOfDay), formatDate(endOfDay)]
  filters.value.start_date = formatDate(startOfDay)
  filters.value.end_date = formatDate(endOfDay)

  fetchCache()
})
</script>

<style scoped>
.hot-search-view {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24px;
}

.top-nav {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 24px;
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
}

.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
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

.nav-tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
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

.table-card {
  max-width: 1400px;
}

.filter-form {
  margin: 0;
}

.hot-search-table {
  width: 100%;
}

.title-cell {
  display: flex;
  align-items: center;
}

.description-cell {
  color: #606266;
  line-height: 1.6;
}

.pagination-section {
  display: flex;
  justify-content: center;
  padding: 20px 0 0 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .hot-search-view {
    padding: 16px;
  }

  .top-nav {
    margin: -16px -16px 16px -16px;
  }

  .filter-form {
    flex-direction: column;
  }

  .filter-form .el-form-item {
    width: 100%;
    margin-right: 0;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }
}

/* 描述列tooltip样式限制 */
:deep(.el-tooltip__popper) {
  max-width: 500px !important;
  word-wrap: break-word !important;
  word-break: break-word !important;
}

:deep(.el-popper.el-tooltip) {
  max-width: 500px !important;
}
</style>
