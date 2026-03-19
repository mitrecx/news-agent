<template>
  <div class="weibo-manage-view">
    <AppNav :full-width="true" />

    <!-- 内容区域 -->
    <div class="manage-content">
      <!-- 统计卡片 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :xs="24" :sm="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon total">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total_items }}</div>
                <div class="stat-label">总热搜数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon has-description">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.has_description_count }}</div>
                <div class="stat-label">已有描述</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon missing">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.missing_count }}</div>
                <div class="stat-label">缺少描述</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 抓取微博热搜 -->
      <el-card class="action-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">抓取微博热搜</span>
          </div>
        </template>

        <div class="action-content">
          <div class="action-description">
            <p>手动触发抓取最新的微博热搜列表。系统将获取当前热搜并保存到数据库。</p>
            <p class="tip">提示：每次最多可抓取 {{ maxHotSearchLimit }} 条热搜，新增的热搜将自动触发描述生成任务。</p>
          </div>

          <div class="action-controls">
            <el-input-number
              v-model="hotSearchLimit"
              :min="10"
              :max="maxHotSearchLimit"
              :step="10"
              label="抓取数量"
              style="width: 200px; margin-right: 12px"
            />
            <el-button
              type="success"
              :icon="Download"
              :loading="fetchingHotSearch"
              @click="handleFetchHotSearch"
            >
              {{ fetchingHotSearch ? '抓取中...' : '开始抓取热搜' }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats">
              刷新统计
            </el-button>
          </div>
        </div>

        <!-- 热搜抓取结果 -->
        <div v-if="hotSearchResult" class="task-results">
          <el-divider content-position="left">
            <span class="divider-text">抓取结果</span>
          </el-divider>
          <div class="results-summary">
            <el-tag type="success" size="large">
              抓取完成！共 {{ hotSearchResult.total_fetched }} 条
            </el-tag>
            <span class="note">
              新增 {{ hotSearchResult.new_items }} 条，
              重复 {{ hotSearchResult.cached_items }} 条
            </span>
          </div>
          <el-table :data="hotSearchResult.items" class="results-table" max-height="400" stripe>
            <el-table-column prop="rank" label="排名" width="80" />
            <el-table-column prop="title" label="热搜标题" min-width="250" show-overflow-tooltip />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'new'" type="success" size="small">
                  新增
                </el-tag>
                <el-tag v-else type="info" size="small">
                  重复
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="保存状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'new' && row.saved" type="success" size="small">
                  已保存
                </el-tag>
                <el-tag v-else-if="row.status === 'new' && !row.saved" type="warning" size="small">
                  <el-icon><Warning /></el-icon>
                  未保存
                </el-tag>
                <el-tag v-else type="info" size="small">
                  -
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 操作区域 -->
      <el-card class="action-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">批量抓取描述</span>
          </div>
        </template>

        <div class="action-content">
          <div class="action-description">
            <p>手动触发抓取微博热搜详情描述任务。系统将为缺少描述的热搜生成详情内容。</p>
            <p class="tip">提示：每次最多可处理 {{ maxFetchLimit }} 条热搜，建议分批处理。</p>
          </div>

          <div class="action-controls">
            <el-input-number
              v-model="fetchLimit"
              :min="1"
              :max="maxFetchLimit"
              :step="5"
              label="处理数量"
              style="width: 200px; margin-right: 12px"
            />
            <el-button
              type="primary"
              :icon="Lightning"
              :loading="fetching"
              :disabled="stats.missing_count === 0"
              @click="handleFetchMissing"
            >
              {{ fetching ? '处理中...' : '开始抓取' }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats">
              刷新统计
            </el-button>
          </div>
        </div>

        <!-- 任务结果 -->
        <div v-if="taskResults.length > 0" class="task-results">
          <el-divider content-position="left">
            <span class="divider-text">任务结果</span>
          </el-divider>
          <div class="results-summary">
            <el-tag type="success" size="large">
              已触发 {{ taskResults.length }} 个任务
            </el-tag>
            <span class="note">任务将在后台异步执行，请稍后刷新查看结果</span>
          </div>
          <el-table :data="taskResults" class="results-table" max-height="300">
            <el-table-column prop="title" label="热搜标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="task_id" label="任务ID" width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'queued'" type="info" size="small">
                  已排队
                </el-tag>
                <el-tag v-else type="info" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 缺失描述列表 -->
      <el-card class="list-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">缺少描述的热搜（前20条）</span>
            <el-button text :icon="Refresh" @click="loadStats" :loading="loading">
              刷新
            </el-button>
          </div>
        </template>

        <el-table
          :data="stats.missing_items"
          v-loading="loading"
          stripe
          class="missing-table"
        >
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="title" label="热搜标题" min-width="300" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="stats.missing_items.length === 0 && !loading"
          description="暂无缺失描述的热搜"
          :image-size="100"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  CircleCheck,
  Warning,
  Lightning,
  Refresh,
  Download,
} from '@element-plus/icons-vue'
import {
  getMissingDescriptionStats,
  fetchMissingDescriptions,
  fetchHotSearch,
  type MissingDescriptionStats,
  type TaskResult,
  type FetchHotSearchResponse
} from '@/api/hotsearch'
import AppNav from '@/components/AppNav.vue'

// 数据
const stats = ref<MissingDescriptionStats>({
  total_items: 0,
  missing_count: 0,
  has_description_count: 0,
  missing_items: []
})
const loading = ref(false)
const fetching = ref(false)
const fetchingHotSearch = ref(false)
const taskResults = ref<TaskResult[]>([])
const fetchLimit = ref(10)
const maxFetchLimit = ref(50)
const hotSearchLimit = ref(50)
const maxHotSearchLimit = ref(100)
const hotSearchResult = ref<FetchHotSearchResponse | null>(null)

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
  })
}

// 加载统计数据
const loadStats = async () => {
  loading.value = true
  try {
    const response = await getMissingDescriptionStats()
    stats.value = response.data
    taskResults.value = [] // 清空之前的任务结果
  } catch (error: any) {
    ElMessage.error(error.message || '获取统计数据失败')
    console.error('获取统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理抓取缺失描述
const handleFetchMissing = async () => {
  if (stats.value.missing_count === 0) {
    ElMessage.warning('没有缺失描述的热搜需要处理')
    return
  }

  fetching.value = true
  try {
    const response = await fetchMissingDescriptions({
      limit: fetchLimit.value
    })

    taskResults.value = response.data.items

    if (response.data.total_queued > 0) {
      ElMessage.success(`已触发 ${response.data.total_queued} 个抓取任务`)
      // 3秒后自动刷新统计数据
      setTimeout(() => {
        loadStats()
      }, 3000)
    } else {
      ElMessage.info('没有需要处理的任务')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '触发抓取任务失败')
    console.error('触发抓取任务失败:', error)
  } finally {
    fetching.value = false
  }
}

// 处理抓取微博热搜
const handleFetchHotSearch = async () => {
  fetchingHotSearch.value = true
  try {
    const response = await fetchHotSearch({
      limit: hotSearchLimit.value
    })

    hotSearchResult.value = response.data

    const newCount = response.data.new_items
    const dupCount = response.data.cached_items

    if (newCount > 0) {
      ElMessage.success(`抓取完成！新增 ${newCount} 条，重复 ${dupCount} 条`)
    } else {
      ElMessage.info(`抓取完成，但所有热搜都已存在（共 ${dupCount} 条重复）`)
    }

    // 5秒后自动刷新统计数据
    setTimeout(() => {
      loadStats()
      // 不清空结果显示，让用户可以查看详细状态
    }, 3000)
  } catch (error: any) {
    ElMessage.error(error.message || '触发热搜抓取任务失败')
    console.error('触发热搜抓取任务失败:', error)
  } finally {
    fetchingHotSearch.value = false
  }
}

// 初始化
onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.weibo-manage-view {
  min-height: 100vh;
  background: #f5f7fa;
}

.manage-content {
  max-width: 1600px;
  margin: 0 auto 24px auto;
  padding: 0;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.stat-icon.total {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-icon.has-description {
  background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
  color: white;
}

.stat-icon.missing {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

/* 操作卡片 */
.action-card,
.list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.action-content {
  margin-bottom: 16px;
}

.action-description {
  margin-bottom: 20px;
  color: #606266;
  line-height: 1.8;
}

.action-description .tip {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}

.action-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

/* 任务结果 */
.task-results {
  margin-top: 20px;
}

.divider-text {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.results-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.results-summary .note {
  font-size: 13px;
  color: #909399;
}

.results-table {
  margin-top: 12px;
}

.result-details {
  margin-top: 16px;
}

/* 表格样式 */
.missing-table {
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .manage-content {
    margin: 16px;
  }

  .stats-row {
    margin-bottom: 16px;
  }

  .stat-card {
    margin-bottom: 12px;
  }

  .stat-value {
    font-size: 24px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    font-size: 24px;
  }

  .action-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .action-controls .el-input-number {
    width: 100% !important;
  }
}
</style>
