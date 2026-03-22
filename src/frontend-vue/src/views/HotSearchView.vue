<template>
  <div class="hot-search-view">
    <AppNav :full-width="true" />

    <!-- 内容区域 -->
    <div class="hot-search-content">
      <!-- 数据表格 -->
      <el-card class="table-card">
      <template #header>
        <!-- 抓取功能区域 -->
        <div class="fetch-section">
          <!-- 抓取微博热搜 -->
          <div class="fetch-item">
            <div class="fetch-item-content">
              <el-input-number
                v-model="hotSearchLimit"
                :min="10"
                :max="100"
                :step="10"
                placeholder="数量"
                style="width: 150px"
              />
              <el-button
                type="success"
                :icon="Download"
                :loading="fetchingHotSearch"
                @click="handleFetchHotSearch"
              >
                抓取微博热搜
              </el-button>
              <el-tag type="info" size="large" class="total-badge">
                总计: {{ totalCount }} 条
              </el-tag>
            </div>
          </div>

          <!-- 抓取热搜描述 -->
          <div class="fetch-item">
            <div class="fetch-item-content">
              <el-input-number
                v-model="fetchLimit"
                :min="1"
                :max="50"
                :step="5"
                placeholder="数量"
                style="width: 150px"
              />
              <el-button
                type="primary"
                :icon="Lightning"
                :loading="fetching"
                @click="handleFetchMissing"
              >
                抓取热搜描述
              </el-button>
            </div>
          </div>
        </div>

        <!-- 分隔线 -->
        <el-divider style="margin: 16px 0;" />

        <!-- 查询表单 -->
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
            <el-button
              @click="toggleAllDescriptions"
              :type="allExpanded ? 'primary' : 'default'"
            >
              {{ allExpanded ? '全部收起' : '全部展开' }}
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <!-- 批量操作按钮 -->
      <div v-if="selectedItems.length > 0" class="batch-actions">
        <el-alert
          :title="`已选择 ${selectedItems.length} 条热搜`"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <el-button
              type="danger"
              :icon="Delete"
              :loading="deleting"
              @click="handleBatchDelete"
            >
              批量删除
            </el-button>
            <el-button @click="handleClearSelection">
              取消选择
            </el-button>
          </template>
        </el-alert>
      </div>

      <el-table
        ref="tableRef"
        :data="cacheItems"
        v-loading="loading"
        stripe
        class="hot-search-table"
        :default-sort="{ prop: 'updated_at', order: 'descending' }"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column type="index" label="#" width="80" :index="indexMethod" class-name="index-column" />

        <el-table-column prop="title" label="热搜标题" min-width="200">
          <template #default="{ row }">
            <div class="title-cell">
              <div class="title-content">
                <el-tag v-if="row.description_source === 'weibo_detail'" size="small" type="success" style="margin-right: 8px">
                  微博
                </el-tag>
                {{ row.title }}
              </div>
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                link
                @click="handleDelete(row.title)"
                :loading="deletingItem === row.title"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="500">
          <template #default="{ row }">
            <div class="description-cell-wrapper">
              <div
                class="description-cell"
                :class="isDescriptionExpanded(row.title) ? '' : 'description-compact'"
              >
                {{ row.description || '-' }}
              </div>
              <el-button
                v-if="row.description && row.description.length > 100"
                type="primary"
                link
                size="small"
                @click="toggleDescription(row.title)"
                class="toggle-btn"
              >
                {{ isDescriptionExpanded(row.title) ? '收起' : '展开' }}
              </el-button>
            </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Download, Lightning, Delete } from '@element-plus/icons-vue'
import { getWeiboHotSearchCache, fetchMissingDescriptions, fetchHotSearch, deleteHotSearch, batchDeleteHotSearches, type HotSearchCacheItem } from '@/api/hotsearch'
import AppNav from '@/components/AppNav.vue'
import type { ElTable } from 'element-plus'

// 表格引用
const tableRef = ref<InstanceType<typeof ElTable>>()

// 数据
const cacheItems = ref<HotSearchCacheItem[]>([])
const loading = ref(false)
const total = ref(0)
const totalCount = ref(0) // 数据库总条数
const currentPage = ref(1)
const pageSize = ref(15)

// 抓取功能相关
const fetching = ref(false)
const fetchingHotSearch = ref(false)
const fetchLimit = ref(3)
const hotSearchLimit = ref(50)

// 删除相关
const selectedItems = ref<string[]>([])
const deleting = ref(false)
const deletingItem = ref<string | null>(null)

// 展开的描述行（使用 title 作为唯一标识）
const expandedDescriptions = ref<Set<string>>(new Set())

// 检查当前页所有项是否都已展开
const allExpanded = computed(() => {
  if (cacheItems.value.length === 0) return false
  return cacheItems.value.every(item => expandedDescriptions.value.has(item.title))
})

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

// 获取数据库总条数（不受过滤条件影响）
const fetchTotalCount = async () => {
  try {
    const response = await getWeiboHotSearchCache({
      limit: 1, // 只需要获取总数，不关心具体数据
      offset: 0,
    })
    totalCount.value = response.data.total
  } catch (error: any) {
    console.error('获取总条数失败:', error)
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

// 处理选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedItems.value = selection.map((item: any) => item.title)
}

// 处理清除选择
const handleClearSelection = () => {
  tableRef.value?.clearSelection()
  selectedItems.value = []
}

// 处理单个删除
const handleDelete = async (title: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除热搜"${title}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    deletingItem.value = title
    try {
      await deleteHotSearch(title)
      ElMessage.success('删除成功')
      selectedItems.value = []
      await Promise.all([fetchCache(), fetchTotalCount()])
    } catch (error: any) {
      ElMessage.error(error.message || '删除失败')
    } finally {
      deletingItem.value = null
    }
  } catch (error: any) {
    // 用户取消删除，不做任何操作
  }
}

// 处理批量删除
const handleBatchDelete = async () => {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('请先选择要删除的热搜')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedItems.value.length} 条热搜吗？此操作不可恢复。`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    deleting.value = true
    try {
      const response = await batchDeleteHotSearches(selectedItems.value)
      ElMessage.success(`成功删除 ${response.data.count} 条热搜`)
      selectedItems.value = []
      await Promise.all([fetchCache(), fetchTotalCount()])
    } catch (error: any) {
      ElMessage.error(error.message || '批量删除失败')
    } finally {
      deleting.value = false
    }
  } catch (error: any) {
    // 用户取消删除，不做任何操作
  }
}

// 处理抓取微博热搜
const handleFetchHotSearch = async () => {
  fetchingHotSearch.value = true
  try {
    const response = await fetchHotSearch({
      limit: hotSearchLimit.value
    })

    const newCount = response.data.new_items
    const dupCount = response.data.cached_items

    if (newCount > 0) {
      ElMessage.success(`抓取完成！新增 ${newCount} 条，重复 ${dupCount} 条`)
    } else {
      ElMessage.info(`抓取完成，但所有热搜都已存在（共 ${dupCount} 条重复）`)
    }

    // 3秒后自动刷新数据和总条数
    setTimeout(() => {
      Promise.all([fetchCache(), fetchTotalCount()])
    }, 3000)
  } catch (error: any) {
    ElMessage.error(error.message || '抓取热搜失败')
    console.error('抓取热搜失败:', error)
  } finally {
    fetchingHotSearch.value = false
  }
}

// 处理批量抓取描述
const handleFetchMissing = async () => {
  fetching.value = true
  try {
    const response = await fetchMissingDescriptions({
      limit: fetchLimit.value
    })

    const successCount = response.data.success_count || 0
    const failedCount = response.data.failed_count || 0
    const totalCount = response.data.total_queued

    if (totalCount > 0) {
      if (failedCount === 0) {
        ElMessage.success(`批量抓取完成！成功 ${successCount} 条`)
      } else if (successCount === 0) {
        ElMessage.error(`批量抓取失败！${failedCount} 条全部失败`)
      } else {
        ElMessage.warning(`批量抓取完成！成功 ${successCount} 条，失败 ${failedCount} 条`)
      }

      // 3秒后自动刷新数据和总条数
      setTimeout(() => {
        Promise.all([fetchCache(), fetchTotalCount()])
      }, 3000)
    } else {
      ElMessage.info('没有需要处理的任务')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '批量抓取描述失败')
    console.error('批量抓取描述失败:', error)
  } finally {
    fetching.value = false
  }
}

// 切换单行描述的展开/收起状态
const toggleDescription = (title: string) => {
  if (expandedDescriptions.value.has(title)) {
    expandedDescriptions.value.delete(title)
  } else {
    expandedDescriptions.value.add(title)
  }
}

// 检查描述是否展开
const isDescriptionExpanded = (title: string) => {
  return expandedDescriptions.value.has(title)
}

// 切换所有描述的展开/收起状态
const toggleAllDescriptions = () => {
  if (allExpanded.value) {
    // 全部收起
    expandedDescriptions.value.clear()
  } else {
    // 全部展开
    cacheItems.value.forEach(item => {
      expandedDescriptions.value.add(item.title)
    })
  }
}

// 初始化
onMounted(async () => {
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

  // 并行获取缓存数据和总条数
  await Promise.all([fetchCache(), fetchTotalCount()])
})
</script>

<style scoped>
.hot-search-view {
  min-height: 100vh;
  background: #f5f7fa;
}

.hot-search-content {
  max-width: 1600px;
  margin: 0 auto 24px auto;
  padding: 0;
}

.table-card {
  /* 让卡片充满容器，并添加适当的间距 */
  margin-bottom: 24px;
}

.filter-form {
  margin: 0;
}

/* 抓取功能区域 */
.fetch-section {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.fetch-item {
  flex: 1;
}

.fetch-item-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.total-badge {
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
}

.hot-search-table {
  width: 100%;
}

/* 表头样式 */
.hot-search-table :deep(.el-table__header-wrapper) {
  th {
    background: #a1edfecc;
    color: #606660;
    font-weight: 600;
    font-size: 14px;
    padding: 16px 12px !important;
  }
}

/* 序号列居中 */
.hot-search-table :deep(.index-column) {
  text-align: center;
}

.hot-search-table :deep(.el-table__row) {
  height: auto !important;
}

.hot-search-table :deep(.el-table__cell) {
  padding: 16px 12px !important;
}

.hot-search-table :deep(.el-table__body-wrapper) {
  overflow-y: auto;
}

.title-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.title-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

/* 批量操作区域 */
.batch-actions {
  margin-bottom: 16px;
}

.description-cell-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.description-cell {
  color: #606266;
  line-height: 1.8;
  word-break: break-word;
  white-space: pre-wrap;
}

.toggle-btn {
  padding: 0;
  height: auto;
  font-size: 13px;
}

/* 简洁模式：只显示1行 */
.description-compact {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination-section {
  display: flex;
  justify-content: center;
  padding: 20px 0 0 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .hot-search-content {
    margin: 16px;
  }

  .table-card {
    /* 移动端卡片不需要特殊样式 */
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
