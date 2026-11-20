<template>
  <div class="news-page">
    <section class="collection-bar surface" aria-label="采集与摘要操作">
      <div class="collection-metrics">
        <span
          ><strong>{{ statistics.total_items }}</strong> 条资讯</span
        ><i /><span
          ><strong>{{ statistics.has_description_count }}</strong> 已生成摘要</span
        ><span class="pending-count">{{ statistics.missing_count }} 条待生成</span>
      </div>
      <div class="collection-actions">
        <el-button :icon="Refresh" :loading="loading" @click="refresh">刷新</el-button>
        <div class="generate-control">
          <el-select v-model="collectLimit" aria-label="热搜采集数量" style="width: 70px">
            <el-option
              v-for="count in [10, 30, 50]"
              :key="count"
              :label="`${count} 条`"
              :value="count"
            />
          </el-select>
          <el-button :loading="collecting" @click="collect">采集热搜</el-button>
        </div>
        <div class="generate-control">
          <el-select v-model="summaryLimit" aria-label="摘要生成数量" style="width: 70px"
            ><el-option
              v-for="count in [1, 3, 5, 10]"
              :key="count"
              :label="`${count} 条`"
              :value="count" /></el-select
          ><el-button
            type="primary"
            :icon="MagicStick"
            :loading="generating"
            :disabled="!!generatingHash"
            title="按所选数量，依次为待处理资讯生成摘要"
            @click="generateBatch"
            >{{ generating ? '批量生成中' : '批量生成摘要' }}</el-button
          >
        </div>
      </div>
    </section>
    <div v-if="!settings.cookieReady" class="connection-banner">
      <el-icon><InfoFilled /></el-icon>连接微博后，可以获取正文并生成摘要。<RouterLink
        to="/settings?tab=weibo"
        >前往连接 →</RouterLink
      >
    </div>
    <div v-if="jobResult" class="job-result" :class="{ failed: jobResult.failed }" role="status">
      <el-icon><CircleCheck v-if="!jobResult.failed" /><Warning v-else /></el-icon
      ><span>{{ jobResult.message }}</span
      ><button class="icon-button" aria-label="关闭处理结果" @click="jobResult = null">
        <el-icon><Close /></el-icon>
      </button>
    </div>
    <section class="news-workspace surface">
      <div class="news-toolbar">
        <div class="feed-title">
          <span class="feed-marker" />资讯库<span class="result-count">{{ total }}</span>
        </div>
        <div class="feed-filters">
          <el-input
            v-model="search"
            placeholder="搜索热点标题"
            clearable
            :prefix-icon="Search"
            @keyup.enter="applyFilters"
            @clear="applyFilters"
          /><el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="—"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :clearable="true"
            @change="applyFilters"
          /><el-button @click="applyFilters">筛选</el-button>
        </div>
      </div>
      <div v-if="selectedTitles.size" class="selection-bar">
        <span>已选择 {{ selectedTitles.size }} 条</span
        ><button @click="selectedTitles = new Set()">取消选择</button
        ><el-button size="small" type="danger" plain @click="removeSelected">删除所选</el-button>
      </div>
      <div class="news-columns">
        <section class="feed-column" aria-label="热搜列表" v-loading="loading">
          <div class="feed-column-label">
            <span>资讯 · 按更新时间排列</span
            ><span>{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
          </div>
          <div v-if="error" class="empty-state">
            <strong>资讯加载失败</strong>
            <p>{{ error }}</p>
            <el-button @click="refresh">重试</el-button>
          </div>
          <div v-else-if="!items.length && !loading" class="empty-state">
            <el-icon :size="28"><Reading /></el-icon><strong>这里还没有资讯</strong>
            <p>采集微博热搜，或调整筛选条件。</p>
            <el-button @click="resetFilters">清除筛选</el-button>
          </div>
          <div v-else class="feed-list" role="region" aria-label="资讯列表滚动区" tabindex="0">
            <article
              v-for="(item, index) in items"
              :key="item.title_hash"
              class="feed-row"
              :class="{ active: activeItem?.title_hash === item.title_hash }"
            >
              <el-checkbox
                :model-value="selectedTitles.has(item.title)"
                :aria-label="`选择 ${item.title}`"
                @change="toggleSelection(item.title)"
              /><button
                class="feed-story"
                :aria-label="`阅读 ${item.title}`"
                @click="activeHash = item.title_hash"
              >
                <span class="story-meta"
                  ><span class="story-number">{{
                    String((page - 1) * pageSize + index + 1).padStart(2, '0')
                  }}</span
                  ><span>{{ shortDate(item.updated_at) }}</span
                  ><span v-if="item.description" class="summary-ready"><i />已生成摘要</span></span
                >
                <h2>{{ item.title }}</h2>
                <p v-if="item.description">
                  {{ cleanSummary(item.description) }}
                </p>
                <p v-else class="awaiting-summary">等待生成摘要</p></button
              ><span v-if="activeItem?.title_hash === item.title_hash" class="story-arrow">↗</span>
            </article>
          </div>
          <footer class="feed-pagination">
            <span>共 {{ total }} 条</span
            ><el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next"
              :pager-count="5"
              size="small"
              @current-change="loadItems"
            />
          </footer>
        </section>
        <article v-if="activeItem" class="reader-column" aria-label="资讯详情">
          <div class="reader-kicker">
            <span
              ><el-icon><Document /></el-icon>资讯详情</span
            >
            <div>
              <button
                class="icon-button"
                title="删除资讯"
                aria-label="删除当前资讯"
                @click="removeOne(activeItem.title)"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </div>
          <div
            :key="activeItem.title_hash"
            class="reader-body"
            role="region"
            aria-label="资讯正文滚动区"
            tabindex="0"
          >
            <div class="reader-meta">
              <span class="weibo-symbol">热</span><span>微博热搜</span><i />{{
                fullDate(activeItem.updated_at)
              }}
            </div>
            <h2>{{ activeItem.title }}</h2>
            <span class="reader-rule" />
            <div v-if="activeItem.description" class="reader-summary">
              <span class="summary-label"
                ><el-icon><MagicStick /></el-icon
                >{{ activeItem.description.startsWith('截断:') ? '正文节选' : 'AI 内容摘要' }}</span
              >
              <p>{{ cleanSummary(activeItem.description) }}</p>
              <div class="summary-footnote">摘要基于微博公开内容生成，请结合原文判断。</div>
            </div>
            <div v-else class="reader-empty">
              <span class="reader-empty-icon"
                ><el-icon><MagicStick /></el-icon
              ></span>
              <h3>这条资讯还没有内容摘要</h3>
              <p>只获取当前话题的微博内容，并生成摘要。</p>
              <el-button
                :loading="generatingHash === activeItem.title_hash"
                :disabled="
                  generating || (!!generatingHash && generatingHash !== activeItem.title_hash)
                "
                @click="generateCurrent"
                >{{
                  generatingHash === activeItem.title_hash ? '正在获取本条详情' : '获取本条详情'
                }}
                <el-icon><ArrowRight /></el-icon
              ></el-button>
              <p
                v-if="singleError?.titleHash === activeItem.title_hash"
                class="single-summary-error"
                role="alert"
              >
                {{ singleError.message }}
              </p>
            </div>
            <div class="reader-actions">
              <el-button
                v-if="activeItem.url"
                tag="a"
                :href="activeItem.url"
                target="_blank"
                rel="noopener noreferrer"
                >阅读微博原文 <el-icon><TopRight /></el-icon></el-button
              ><el-button type="primary" plain @click="discuss(activeItem.title)"
                >与 AI 聊聊 <el-icon><ChatLineRound /></el-icon
              ></el-button>
            </div>
          </div>
          <div class="reader-bottom">
            <span class="status-dot" />NEWS AGENT
            <span>多一份理解，少一点噪声。</span>
          </div>
        </article>
        <div v-else class="reader-column reader-placeholder">
          <el-icon :size="42"><Reading /></el-icon>
          <h2>留一点时间，了解世界。</h2>
          <p>选择左侧资讯，在这里阅读摘要。</p>
        </div>
      </div>
    </section>
    <footer class="page-footnote">
      <span>数据来自微博公开热搜</span
      ><span>按用户配置生成 · {{ settings.model?.name || '未选择模型' }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  MagicStick,
  Document,
  Reading,
  Delete,
  TopRight,
  ChatLineRound,
  ArrowRight,
  CircleCheck,
  Warning,
  InfoFilled,
  Close,
} from '@element-plus/icons-vue'
import {
  getWeiboHotSearchCache,
  getMissingDescriptionStats,
  fetchHotSearch,
  fetchMissingDescriptions,
  fetchStorySummary,
  deleteHotSearch,
  batchDeleteHotSearches,
  type HotSearchCacheItem,
} from '@/api/hotsearch'
import { useSettingsStore } from '@/stores/settings'
const router = useRouter()
const settings = useSettingsStore()
const items = ref<HotSearchCacheItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const activeHash = ref('')
const search = ref('')
const dateRange = ref<[string, string] | null>(null)
const loading = ref(false)
const collecting = ref(false)
const generating = ref(false)
const generatingHash = ref('')
const singleError = ref<{ titleHash: string; message: string } | null>(null)
const error = ref('')
const collectLimit = ref(50)
const summaryLimit = ref(3)
const selectedTitles = ref(new Set<string>())
const jobResult = ref<{ message: string; failed: boolean } | null>(null)
const statistics = ref({
  total_items: 0,
  has_description_count: 0,
  missing_count: 0,
})
const activeItem = computed(
  () => items.value.find((item) => item.title_hash === activeHash.value) || items.value[0],
)
let requestSequence = 0
const message = (value: unknown) => {
  const detail = (value as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : '服务暂时不可用，请稍后重试'
}
const cleanSummary = (text: string) => text.replace(/^(Agent总结|截断)[:：]\s*/, '')
const shortDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
const fullDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
const loadItems = async () => {
  const sequence = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const data = (
      await getWeiboHotSearchCache({
        limit: pageSize,
        offset: (page.value - 1) * pageSize,
        search: search.value.trim() || undefined,
        start_date: dateRange.value?.[0] ? `${dateRange.value[0]}T00:00:00` : undefined,
        end_date: dateRange.value?.[1] ? `${dateRange.value[1]}T23:59:59.999999` : undefined,
      })
    ).data
    if (sequence !== requestSequence) return
    if (!data.items.length && data.total > 0 && page.value > 1) {
      page.value = Math.max(1, Math.ceil(data.total / pageSize))
      await loadItems()
      return
    }
    items.value = data.items
    total.value = data.total
    selectedTitles.value = new Set()
  } catch (failure) {
    if (sequence === requestSequence) error.value = message(failure)
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}
const refreshStatistics = async () => {
  try {
    statistics.value = (await getMissingDescriptionStats()).data
  } catch {
    // 统计暂时不可用不影响已获取的资讯内容。
  }
}
const refresh = async () => {
  await Promise.all([loadItems(), refreshStatistics()])
}
const applyFilters = () => {
  page.value = 1
  loadItems()
}
const resetFilters = () => {
  search.value = ''
  dateRange.value = null
  applyFilters()
}
const toggleSelection = (title: string) => {
  const next = new Set(selectedTitles.value)
  if (next.has(title)) next.delete(title)
  else next.add(title)
  selectedTitles.value = next
}
const collect = async () => {
  collecting.value = true
  jobResult.value = null
  try {
    const data = (await fetchHotSearch({ limit: collectLimit.value })).data
    jobResult.value = {
      message: `采集完成，新增 ${data.new_items} 条，已有 ${data.cached_items} 条。`,
      failed: false,
    }
    page.value = 1
    await refresh()
  } catch (failure) {
    jobResult.value = { message: message(failure), failed: true }
  } finally {
    collecting.value = false
  }
}
const generateBatch = async () => {
  if (generating.value || generatingHash.value) return
  if (!settings.model) {
    ElMessage.warning('请先在设置中添加并启用一个模型')
    return
  }
  generating.value = true
  jobResult.value = null
  try {
    const data = (await fetchMissingDescriptions({ limit: summaryLimit.value })).data
    jobResult.value = {
      message:
        data.total_queued === 0
          ? '所有资讯都已有摘要，无需重复生成。'
          : `摘要生成完成：成功 ${data.success_count} 条${data.failed_count ? `，失败 ${data.failed_count} 条。${data.items.find((item) => item.error)?.error || ''}` : '。'}`,
      failed: data.failed_count > 0,
    }
    page.value = 1
    await refresh()
  } catch (failure) {
    jobResult.value = { message: message(failure), failed: true }
  } finally {
    generating.value = false
  }
}
const generateCurrent = async () => {
  const target = activeItem.value
  if (!target || generating.value || generatingHash.value) return
  if (!settings.model) {
    ElMessage.warning('请先在设置中添加并启用一个模型')
    return
  }
  generatingHash.value = target.title_hash
  singleError.value = null
  try {
    const data = (await fetchStorySummary(target.title_hash)).data
    items.value = items.value.map((item) =>
      item.title_hash === data.item.title_hash ? data.item : item,
    )
    await refreshStatistics()
    ElMessage.success('本条资讯详情已更新')
  } catch (failure) {
    singleError.value = { titleHash: target.title_hash, message: message(failure) }
  } finally {
    generatingHash.value = ''
  }
}
const removeOne = async (title: string) => {
  try {
    await ElMessageBox.confirm(`确定删除「${title}」？`, '删除资讯', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteHotSearch(title)
    await refresh()
    ElMessage.success('资讯已删除')
  } catch (failure) {
    ElMessage.error(message(failure))
  }
}
const removeSelected = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedTitles.value.size} 条资讯？`, '删除资讯', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await batchDeleteHotSearches([...selectedTitles.value])
    await refresh()
    ElMessage.success('所选资讯已删除')
  } catch (failure) {
    ElMessage.error(message(failure))
  }
}
const discuss = (title: string) => router.push({ path: '/chat', query: { topic: title } })
onMounted(refresh)
</script>

<style scoped>
.news-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  gap: 16px;
}
.collection-bar {
  padding: 17px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}
.collection-metrics {
  display: flex;
  align-items: center;
  gap: 17px;
  font-size: 10px;
  color: #8a9ca6;
  white-space: nowrap;
}
.collection-metrics strong {
  font-size: 19px;
  font-weight: 600;
  color: #486473;
  margin-right: 5px;
  font-variant-numeric: tabular-nums;
}
.collection-metrics i {
  height: 23px;
  width: 1px;
  background: var(--line);
}
.pending-count {
  color: #a0acb3;
  font-size: 9px;
}
.collection-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.button-count {
  border-left: 1px solid #e4eaed;
  padding-left: 10px;
  margin-left: 10px;
  font-size: 10px;
  color: #8f9da6;
}
.generate-control {
  display: flex;
  align-items: center;
}
.generate-control .el-button {
  margin-left: 5px;
}
.generate-control :deep(.el-select__wrapper) {
  box-shadow: none;
  background: #f6f8f9;
  font-size: 10px;
}
.connection-banner {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: #ab8968;
  background: #fdf7ed;
  padding: 13px 16px;
  border-radius: 8px;
  flex-shrink: 0;
}
.connection-banner a {
  margin-left: auto;
  color: #8d775e;
  white-space: nowrap;
}
.job-result {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4d8b70;
  background: #eaf5ee;
  border: 1px solid #dcece1;
  padding: 8px 14px;
  border-radius: 8px;
  flex-shrink: 0;
  font-size: 11px;
}
.job-result.failed {
  color: #ad805c;
  background: #fff4e9;
  border-color: #f2e6d9;
}
.job-result .icon-button {
  margin-left: auto;
}
.news-workspace {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.news-toolbar {
  display: flex;
  flex-shrink: 0;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 20px 22px;
  border-bottom: 1px solid var(--line);
}
.feed-title {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.feed-marker {
  width: 3px;
  height: 12px;
  background: #57998c;
  border-radius: 2px;
}
.result-count {
  padding: 3px 6px;
  font-size: 9px;
  font-weight: 500;
  border-radius: 4px;
  background: #f0f4f5;
  color: #94a1a9;
  margin-left: 2px;
}
.feed-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
}
.feed-filters > .el-input {
  max-width: 180px;
}
.feed-filters :deep(.el-date-editor) {
  width: 220px;
  flex-grow: 0;
}
.feed-filters :deep(.el-input__wrapper),
.feed-filters :deep(.el-range-editor) {
  box-shadow: 0 0 0 1px #e9eef0 inset;
  font-size: 10px;
}
.feed-filters :deep(.el-range-input) {
  font-size: 10px;
}
.news-columns {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(270px, 0.95fr) minmax(280px, 1.05fr);
  grid-template-rows: minmax(0, 1fr);
  min-height: 0;
}
.feed-column {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
}
.feed-column-label {
  flex-shrink: 0;
  padding: 16px 23px;
  display: flex;
  justify-content: space-between;
  color: #a0adb5;
  font-size: 9px;
}
.feed-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
}
.feed-row {
  display: flex;
  gap: 10px;
  padding: 17px 18px 17px 23px;
  border-bottom: 1px solid #f0f3f4;
  position: relative;
  min-height: 116px;
}
.feed-row.active {
  background: #f0f7f4;
}
.feed-row.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #5b9c89;
}
.feed-row:hover {
  background: #f5f9f7;
}
.feed-row > .el-checkbox {
  align-self: center;
  margin: 0;
}
.feed-row :deep(.el-checkbox__inner) {
  width: 12px;
  height: 12px;
  border-color: #dbe3e6;
}
.feed-row :deep(.el-checkbox__inner::after) {
  left: 3px;
  top: 0;
}
.feed-story {
  text-align: left;
  border: 0;
  background: none;
  min-width: 0;
  flex: 1;
  color: var(--ink);
}
.story-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 8px;
  color: #9cabb2;
}
.story-number {
  font:
    9px Menlo,
    monospace;
  color: #a0afb6;
}
.summary-ready {
  color: #70a38c;
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.summary-ready i {
  width: 4px;
  height: 4px;
  background: #70a38c;
  border-radius: 50%;
}
.feed-story h2 {
  font-size: 12px;
  font-weight: 550;
  line-height: 1.8;
  margin: 7px 0 5px;
}
.feed-story p {
  color: #a0acb3;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.8;
}
.feed-story .awaiting-summary {
  color: #b0bbc1;
  font-size: 9px;
}
.story-arrow {
  color: #6b9c8d;
  align-self: center;
  margin-left: 1px;
}
.feed-pagination {
  flex-shrink: 0;
  padding: 15px 18px 15px 23px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--line);
  margin-top: auto;
}
.feed-pagination > span {
  color: #9ba8b0;
  font-size: 9px;
}
.feed-pagination :deep(.el-pager li) {
  min-width: 23px;
  height: 25px;
  font-size: 10px;
}
.feed-pagination :deep(button) {
  min-width: 22px;
  height: 25px;
}
.reader-column {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.reader-kicker {
  flex-shrink: 0;
  padding: 15px 25px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: #9aabb3;
  border-bottom: 1px solid #f0f3f4;
  min-height: 57px;
}
.reader-kicker > span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.reader-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
  padding: 36px 33px 28px;
}
.feed-list:focus-visible,
.reader-body:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.reader-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 9px;
  color: #a0adb5;
  line-height: 1.8;
}
.reader-meta i {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #bbc5ca;
  margin: 0 2px;
}
.weibo-symbol {
  color: #d48b63;
  background: #fff3e8;
  border-radius: 4px;
  font-size: 8px;
  padding: 0 4px;
}
.reader-body > h2 {
  font-size: 24px;
  line-height: 1.65;
  letter-spacing: -0.5px;
  font-weight: 600;
  margin-top: 21px;
}
.reader-rule {
  display: block;
  width: 28px;
  height: 2px;
  background: #8db5a5;
  margin: 25px 0 30px;
}
.summary-label {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #75a18f;
  font-size: 9px;
}
.reader-summary > p {
  font-size: 12px;
  color: #74858d;
  line-height: 2.5;
  margin-top: 17px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.summary-footnote {
  margin-top: 25px;
  border-left: 2px solid #e0eae5;
  padding: 3px 0 3px 10px;
  color: #b0bac0;
  font-size: 9px;
  line-height: 1.9;
}
.reader-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 33px;
}
.reader-actions .el-button {
  margin: 0;
  height: 33px;
  font-size: 10px;
}
.reader-actions .el-icon {
  margin-left: 12px;
}
.reader-bottom {
  flex-shrink: 0;
  margin: auto 25px 0;
  border-top: 1px solid #f0f3f4;
  padding: 19px 0;
  display: flex;
  gap: 7px;
  align-items: center;
  color: #a3b4b5;
  font-size: 8px;
  letter-spacing: 1px;
}
.reader-bottom .status-dot {
  width: 4px;
  height: 4px;
}
.reader-bottom > span:last-child {
  margin-left: auto;
  color: #b6c1c6;
  letter-spacing: 0.2px;
}
.reader-placeholder {
  align-items: center;
  justify-content: center;
  color: #b7c7c7;
  text-align: center;
  padding: 25px;
}
.reader-placeholder h2 {
  font-size: 17px;
  margin: 23px 0 12px;
  color: #8ca2a4;
  font-weight: 400;
}
.reader-placeholder p {
  color: #a8b6bc;
  font-size: 11px;
}
.reader-empty {
  padding: 12px 0 30px;
}
.reader-empty-icon {
  display: grid;
  place-items: center;
  width: 45px;
  height: 45px;
  background: #f0f6f2;
  color: #93b4a5;
  border-radius: 12px;
  font-size: 21px;
}
.reader-empty h3 {
  font-size: 14px;
  font-weight: 500;
  color: #75918a;
  margin-top: 20px;
}
.reader-empty p {
  margin: 12px 0 22px;
  line-height: 2;
  font-size: 10px;
  color: #9cacb2;
}
.reader-empty .single-summary-error {
  color: #ad805c;
}
.reader-empty .el-button {
  font-size: 10px;
}
.reader-empty .el-icon {
  margin-left: 8px;
}
.page-footnote {
  display: flex;
  flex-shrink: 0;
  justify-content: space-between;
  gap: 12px;
  color: #abb7bf;
  font-size: 9px;
  padding: 0 2px;
}
.selection-bar {
  flex-shrink: 0;
  padding: 9px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid var(--line);
  font-size: 10px;
  color: #6f9b88;
  background: #f8fbf9;
}
.selection-bar > button:not(.el-button) {
  border: none;
  background: none;
  font-size: 10px;
  color: #91a1a9;
}
.selection-bar .el-button {
  margin-left: auto;
}
@media (max-width: 1200px) {
  .collection-bar {
    flex-wrap: wrap;
  }
  .collection-actions {
    margin-left: auto;
  }
  .news-toolbar {
    flex-wrap: wrap;
    gap: 15px;
  }
  .feed-filters {
    width: 100%;
  }
  .feed-filters > .el-input {
    max-width: none;
  }
  .feed-filters :deep(.el-date-editor) {
    width: 230px;
  }
  .reader-body {
    padding: 30px 24px;
  }
  .reader-body > h2 {
    font-size: 21px;
  }
  .summary-ready {
    font-size: 8px;
  }
  .feed-row {
    padding-left: 17px;
    gap: 8px;
  }
  .news-columns {
    grid-template-columns: minmax(240px, 0.95fr) minmax(260px, 1.05fr);
  }
  .pending-count {
    display: none;
  }
}
@media (max-width: 940px) {
  .news-columns {
    flex: none;
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }
  .feed-column {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .feed-list {
    flex: none;
    height: min(52dvh, 480px);
  }
  .reader-body {
    flex: none;
    max-height: min(65dvh, 620px);
    padding: 26px;
  }
  .reader-column {
    min-height: 0;
  }
  .reader-placeholder {
    min-height: 280px;
  }
  .reader-body > h2 {
    font-size: 23px;
  }
  .reader-summary > p {
    font-size: 13px;
  }
  .collection-metrics {
    gap: 12px;
  }
  .collection-actions {
    width: 100%;
    justify-content: space-between;
    margin-top: 3px;
  }
  .feed-filters {
    flex-wrap: wrap;
  }
  .feed-filters :deep(.el-date-editor) {
    width: 210px;
  }
  .feed-filters > .el-input {
    width: 100%;
    flex: none;
  }
}
@media (max-width: 480px) {
  .collection-bar {
    padding: 15px;
  }
  .collection-metrics strong {
    font-size: 17px;
  }
  .collection-metrics {
    font-size: 9px;
  }
  .collection-actions {
    gap: 8px;
  }
  .collection-actions :deep(.el-button) {
    padding: 8px 10px;
    font-size: 10px;
  }
  .button-count {
    padding-left: 7px;
    margin-left: 7px;
  }
  .generate-control :deep(.el-select) {
    width: 62px !important;
  }
  .news-toolbar {
    padding: 17px 15px;
  }
  .feed-filters :deep(.el-date-editor) {
    width: 100%;
  }
  .feed-filters > .el-button {
    width: 100%;
  }
  .reader-body {
    padding: 24px 20px;
  }
  .reader-body > h2 {
    font-size: 21px;
  }
  .page-footnote {
    flex-direction: column;
    gap: 7px;
  }
  .reader-bottom > span:last-child {
    display: none;
  }
}
</style>

<style scoped>
.feed-story h2 {
  font-size: 13px;
}
.feed-story p {
  font-size: 11px;
  color: #8a9ca5;
}
.reader-summary > p {
  font-size: 13px;
  color: #647c85;
  line-height: 2.35;
}
.reader-meta {
  font-size: 10px;
}
.feed-column-label {
  font-size: 10px;
}
</style>
