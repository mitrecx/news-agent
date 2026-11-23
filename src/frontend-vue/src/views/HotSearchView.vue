<template>
  <div v-if="!isDetail" class="news-page">
    <section class="news-heading">
      <div>
        <h1>热点资讯</h1>
        <p class="news-metrics">
          <span>{{ statistics.total_items }} 条资讯</span><i />
          <span>{{ statistics.has_description_count }} 条已有摘要</span><i />
          <span>{{ statistics.missing_count }} 条待处理</span>
        </p>
      </div>
      <div class="news-actions" aria-label="采集与摘要操作">
        <div class="action-group">
          <select v-model.number="collectLimit" aria-label="热搜采集数量" :disabled="busy">
            <option v-for="count in [10, 30, 50]" :key="count" :value="count">{{ count }} 条</option>
          </select>
          <el-button type="primary" :icon="Plus" :loading="collecting" :disabled="busy && !collecting" @click="collect">
            采集热搜
          </el-button>
        </div>
        <el-button class="refresh-button" :icon="Refresh" :loading="loading" :disabled="busy" aria-label="刷新资讯" @click="refresh">
          <span>刷新</span>
        </el-button>
      </div>
    </section>

    <div v-if="!settings.cookieReady" class="connection-notice">
      连接微博后可获取正文并生成摘要。<RouterLink to="/settings?tab=weibo">前往连接</RouterLink>
    </div>
    <div v-if="jobResult" class="job-result" :class="{ failed: jobResult.failed }" role="status">
      <span>{{ jobResult.message }}</span>
      <button class="icon-button" aria-label="关闭处理结果" @click="jobResult = null"><el-icon><Close /></el-icon></button>
    </div>

    <form class="news-filters" aria-label="筛选资讯" @submit.prevent="applyFilters">
      <label class="news-search">
        <el-icon><Search /></el-icon>
        <span class="visually-hidden">搜索标题</span>
        <input v-model="search" type="search" placeholder="搜索标题" @input="scheduleSearch" />
      </label>
      <div class="date-range">
        <input v-model="startDate" type="date" aria-label="开始日期" @change="applyFilters" />
        <span>—</span>
        <input v-model="endDate" type="date" aria-label="结束日期" @change="applyFilters" />
      </div>
      <select v-model="summaryStatus" class="status-filter" aria-label="摘要状态" @change="applyFilters">
        <option value="all">全部摘要状态</option>
        <option value="ready">已有摘要</option>
        <option value="pending">待处理摘要</option>
      </select>
      <button v-if="hasFilters" class="text-button" type="button" @click="resetFilters">清除筛选</button>
      <span class="sort-note">按更新时间排列</span>
    </form>
    <p v-if="dateError" class="filter-error" role="alert">{{ dateError }}</p>

    <section v-loading="loading" class="news-results" aria-label="热搜列表" :aria-busy="loading">
      <div v-if="error" class="news-empty" role="alert">
        <h2>资讯加载失败</h2><p>{{ error }}</p><el-button @click="refresh">重试</el-button>
      </div>
      <div v-else-if="dateError" class="news-empty">
        <h2>请调整日期范围</h2><p>开始日期不能晚于结束日期。</p>
      </div>
      <div v-else-if="!items.length && !loading" class="news-empty">
        <h2>{{ hasFilters ? '没有符合条件的资讯' : '还没有资讯' }}</h2>
        <p>{{ hasFilters ? '换个关键词，或清除筛选后继续浏览。' : '点击上方「采集热搜」获取资讯。' }}</p>
        <el-button v-if="hasFilters" @click="resetFilters">清除筛选</el-button>
      </div>
      <div v-else class="news-table">
        <div class="news-table-head" aria-hidden="true">
          <span>序号</span><span>话题标题</span><span>摘要状态</span><span class="time-column">更新时间</span><span />
        </div>
        <RouterLink v-for="(item, index) in items" :id="`story-${item.title_hash}`" :key="item.title_hash"
          class="news-row" :to="{ name: 'hot-search-detail', params: { titleHash: item.title_hash }, query: route.query }"
          :aria-label="`查看详情：${item.title}`" @click="rememberList(item.title_hash)">
          <span class="row-number">{{ String((page - 1) * pageSize + index + 1).padStart(2, '0') }}</span>
          <h2>{{ item.title }}</h2>
          <span class="summary-state" :class="{ ready: item.description, retrying: item.summary_status === 'retrying' }" :title="item.summary_error || ''">
            <el-icon><Check v-if="item.description" /><Loading v-else-if="item.summary_status === 'processing'" class="is-loading" /><Document v-else /></el-icon>{{ summaryLabel(item) }}
          </span>
          <time class="row-time time-column" :datetime="item.updated_at">{{ formatDate(item.updated_at) }}</time>
          <el-icon class="row-arrow"><ArrowRight /></el-icon>
        </RouterLink>
      </div>
    </section>
    <nav v-if="total && !dateError && !error" class="news-pagination" aria-label="资讯分页">
      <span>共 {{ total }} 条 · 每页 {{ pageSize }} 条</span>
      <div>
        <el-button :disabled="page === 1 || loading" @click="changePage(page - 1)">上一页</el-button>
        <span class="page-number">{{ page }} / {{ pages }}</span>
        <el-button :disabled="page >= pages || loading" @click="changePage(page + 1)">下一页</el-button>
      </div>
    </nav>
    <footer class="news-footnote">采集后自动排队，逐条生成摘要。处理进度自动更新。</footer>
  </div>

  <div v-else class="news-reader">
    <RouterLink class="text-button reader-back" :to="{ name: 'hot-search', query: route.query }">
      <el-icon><Back /></el-icon>返回列表
    </RouterLink>
    <section v-loading="detailLoading" class="reader-sheet" :aria-busy="detailLoading" aria-label="资讯详情">
      <div v-if="detailError" class="news-empty" role="alert">
        <h2>暂时无法查看这条资讯</h2><p>{{ detailError }}</p><el-button @click="loadDetail()">重试</el-button>
      </div>
      <article v-else-if="activeItem">
        <p class="reader-source">微博热搜</p>
        <h1 ref="articleHeading" tabindex="-1">{{ activeItem.title }}</h1>
        <div class="reader-meta">
          <time :datetime="activeItem.updated_at">更新于 {{ formatDate(activeItem.updated_at, true) }}</time>
          <span class="summary-state" :class="{ ready: activeItem.description }">
            <el-icon><Check v-if="activeItem.description" /><Loading v-else-if="activeItem.summary_status === 'processing'" class="is-loading" /><Document v-else /></el-icon>{{ summaryLabel(activeItem) }}
          </span>
        </div>
        <template v-if="activeItem.description">
          <h2 class="article-label">{{ activeItem.description.startsWith('截断:') ? '正文节选' : '内容摘要' }}</h2>
          <p class="article-copy">{{ cleanSummary(activeItem.description) }}</p>
        </template>
        <div v-else class="pending-summary">
          <el-icon><Document /></el-icon>
          <h2>{{ activeItem.summary_status === 'processing' ? '摘要正在生成' : activeItem.summary_status === 'retrying' ? '暂未生成，将自动重试' : '摘要已加入队列' }}</h2>
          <p>{{ activeItem.summary_error || '后台按顺序处理，完成后会自动显示在这里。' }}</p>
          <el-button v-if="activeItem.summary_status === 'retrying'" :loading="generatingHash === activeItem.title_hash" :disabled="busy && generatingHash !== activeItem.title_hash" @click="generateCurrent">重新排队</el-button>
          <p v-if="singleError" class="single-error" role="alert">{{ singleError }}</p>
        </div>
        <div class="reader-actions">
          <el-button v-if="sourceUrl" tag="a" :href="sourceUrl" target="_blank" rel="noopener noreferrer">
            阅读微博原文<el-icon><TopRight /></el-icon>
          </el-button>
          <small>摘要基于公开内容生成，请结合原文判断。</small>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Back, Check, Close, Document, Loading, Plus, Refresh, Search, TopRight } from '@element-plus/icons-vue'
import { fetchHotSearch, fetchStorySummary, getMissingDescriptionStats, getStoryDetail, getWeiboHotSearchCache, type HotSearchCacheItem } from '@/api/hotsearch'
import { useSettingsStore } from '@/stores/settings'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const pageSize = 12
const items = ref<HotSearchCacheItem[]>([])
const activeItem = ref<HotSearchCacheItem | null>(null)
const articleHeading = ref<HTMLElement>()
const total = ref(0)
const page = ref(1)
const search = ref('')
const startDate = ref('')
const endDate = ref('')
const summaryStatus = ref<'all' | 'ready' | 'pending'>('all')
const loading = ref(false)
const detailLoading = ref(false)
const collecting = ref(false)
const generatingHash = ref('')
const error = ref('')
const detailError = ref('')
const singleError = ref('')
const collectLimit = ref(10)
const jobResult = ref<{ message: string; failed: boolean } | null>(null)
const statistics = ref({ total_items: 0, has_description_count: 0, missing_count: 0 })
const isDetail = computed(() => route.name === 'hot-search-detail')
const busy = computed(() => collecting.value || !!generatingHash.value)
const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const dateError = computed(() => startDate.value && endDate.value && startDate.value > endDate.value ? '开始日期不能晚于结束日期。' : '')
const hasFilters = computed(() => !!(search.value || startDate.value || endDate.value || summaryStatus.value !== 'all'))
const sourceUrl = computed(() => {
  try {
    const url = new URL(activeItem.value?.url || '')
    return ['https:', 'http:'].includes(url.protocol) ? url.href : ''
  } catch { return '' }
})
let searchTimer: ReturnType<typeof setTimeout> | undefined
let listRequest = 0
let detailRequest = 0
let routeRequest = 0
let listScroll = 0
let returnHash = ''
let pollTimer: ReturnType<typeof setInterval> | undefined
let polling = false
const summaryLabel = (item: HotSearchCacheItem) => item.description ? '已有摘要' : ({queued: '排队中',processing: '生成中',retrying: '待重试',ready: '已有摘要'}[item.summary_status] || '排队中')

const message = (failure: unknown) => {
  const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : '服务暂时不可用，请稍后重试'
}
const cleanSummary = (value: string) => value.replace(/^(Agent总结|截断)[:：]\s*/, '')
const formatDate = (value: string, full = false) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', { year: full ? 'numeric' : undefined, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date)
}
const queryValue = (key: string) => typeof route.query[key] === 'string' ? route.query[key] as string : ''
const readFilters = () => {
  search.value = queryValue('search')
  startDate.value = /^\d{4}-\d{2}-\d{2}$/.test(queryValue('start')) ? queryValue('start') : ''
  endDate.value = /^\d{4}-\d{2}-\d{2}$/.test(queryValue('end')) ? queryValue('end') : ''
  const status = queryValue('status')
  summaryStatus.value = status === 'ready' || status === 'pending' ? status : 'all'
  const requestedPage = Number(queryValue('page'))
  page.value = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1
}
const listQuery = (targetPage = 1) => ({
  search: search.value.trim() || undefined,
  start: startDate.value || undefined,
  end: endDate.value || undefined,
  status: summaryStatus.value !== 'all' ? summaryStatus.value : undefined,
  page: targetPage > 1 ? String(targetPage) : undefined,
})
const loadItems = async (silent = false) => {
  const sequence = ++listRequest
  if (!silent) { loading.value = true; error.value = '' }
  if (dateError.value) { items.value = []; total.value = 0; loading.value = false; return }
  try {
    const data = (await getWeiboHotSearchCache({ limit: pageSize, offset: (page.value - 1) * pageSize,
      search: search.value.trim() || undefined, status: summaryStatus.value,
      start_date: startDate.value ? `${startDate.value}T00:00:00` : undefined,
      end_date: endDate.value ? `${endDate.value}T23:59:59.999999` : undefined,
    })).data
    if (sequence !== listRequest) return
    if (!data.items.length && data.total > 0 && page.value > 1) {
      await router.replace({ name: 'hot-search', query: listQuery(Math.ceil(data.total / pageSize)) })
      return
    }
    items.value = data.items
    total.value = data.total
  } catch (failure) {
    if (sequence === listRequest && !silent) error.value = message(failure)
  } finally {
    if (sequence === listRequest) loading.value = false
  }
}
const refreshStatistics = async () => {
  try { statistics.value = (await getMissingDescriptionStats()).data } catch { return }
}
const refresh = () => Promise.all([loadItems(), refreshStatistics()])
const loadDetail = async (silent = false) => {
  const sequence = ++detailRequest
  const titleHash = String(route.params.titleHash)
  if (!silent) {
    detailLoading.value = true; detailError.value = ''; singleError.value = ''; activeItem.value = null
  }
  try {
    const item = (await getStoryDetail(titleHash)).data
    if (sequence === detailRequest) activeItem.value = item
  } catch (failure) {
    if (sequence === detailRequest && !silent) detailError.value = message(failure)
  } finally {
    if (sequence === detailRequest) detailLoading.value = false
  }
}
const applyFilters = async () => {
  clearTimeout(searchTimer)
  const target = router.resolve({ name: 'hot-search', query: listQuery() })
  if (route.fullPath === target.fullPath) await loadItems()
  else await router.replace(target.fullPath)
}
const scheduleSearch = () => { clearTimeout(searchTimer); searchTimer = setTimeout(applyFilters, 300) }
const resetFilters = () => {
  search.value = ''; startDate.value = ''; endDate.value = ''; summaryStatus.value = 'all'
  return applyFilters()
}
const changePage = (targetPage: number) => {
  clearTimeout(searchTimer)
  return router.replace({ name: 'hot-search', query: listQuery(targetPage) })
}
const rememberList = (titleHash: string) => { listScroll = window.scrollY; returnHash = titleHash }
const collect = async () => {
  if (busy.value) return
  collecting.value = true
  jobResult.value = null
  try {
    const data = (await fetchHotSearch({ limit: collectLimit.value })).data
    jobResult.value = { message: `采集完成，新增 ${data.new_items} 条，已有 ${data.cached_items} 条。摘要已自动加入处理队列。`, failed: false }
    if (!isDetail.value) {
      if (page.value !== 1) await router.replace({ name: 'hot-search', query: listQuery() })
      else await loadItems()
    }
    await refreshStatistics()
  } catch (failure) { jobResult.value = { message: message(failure), failed: true } }
  finally { collecting.value = false }
}
const generateCurrent = async () => {
  const target = activeItem.value
  if (!target || busy.value) return
  if (!settings.model) { ElMessage.warning('请先在设置中添加并启用一个模型'); return }
  generatingHash.value = target.title_hash
  singleError.value = ''
  try {
    const data = (await fetchStorySummary(target.title_hash)).data
    if (isDetail.value && route.params.titleHash === target.title_hash) activeItem.value = data.item
    await refreshStatistics()
    ElMessage.success(data.status === 'cached' ? '本条摘要已就绪' : '已重新加入摘要队列')
  } catch (failure) {
    if (isDetail.value && route.params.titleHash === target.title_hash) singleError.value = message(failure)
  } finally { generatingHash.value = '' }
}

watch(() => route.fullPath, async (_, previousPath) => {
  const sequence = ++routeRequest
  const returning = !!previousPath?.startsWith('/news/') && !isDetail.value
  clearTimeout(searchTimer)
  if (isDetail.value) {
    ++listRequest
    loading.value = false
    await loadDetail()
  } else {
    ++detailRequest
    readFilters()
    await loadItems()
  }
  if (sequence !== routeRequest) return
  await nextTick()
  window.scrollTo(0, returning ? listScroll : 0)
  if (isDetail.value) articleHeading.value?.focus({ preventScroll: true })
  else if (returning && returnHash) document.getElementById(`story-${returnHash}`)?.focus({ preventScroll: true })
}, { immediate: true })
onMounted(() => {
  refreshStatistics()
  pollTimer = setInterval(async () => {
    if (polling || loading.value || detailLoading.value || busy.value || document.hidden) return
    polling = true
    try {
      if (isDetail.value) { if (activeItem.value && !activeItem.value.description) await loadDetail(true) }
      else if (statistics.value.missing_count && search.value.trim() === queryValue('search')) await loadItems(true)
      await refreshStatistics()
    } finally { polling = false }
  },5000)
})
onBeforeUnmount(() => { clearTimeout(searchTimer); clearInterval(pollTimer); ++listRequest; ++detailRequest; ++routeRequest })
</script>

<style scoped>
.news-page { min-width: 0; }
.news-heading { display: flex; align-items: center; justify-content: space-between; gap: 22px; margin-bottom: 27px; }
.news-heading h1 { font-size: 26px; font-weight: 650; letter-spacing: -.6px; }
.news-metrics { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 12px; margin-top: 7px; }
.news-metrics i { width: 2px; height: 2px; background: #bfc5ce; border-radius: 50%; }
.news-actions { display: flex; align-items: center; gap: 11px; }
.action-group { display: flex; align-items: center; }
.action-group select { height: 35px; min-width: 65px; padding: 0 7px 0 10px; border: 1px solid var(--line); border-right: 0; border-radius: 5px 0 0 5px; background: white; font-size: 12px; }
.action-group .el-button { border-radius: 0 5px 5px 0; }
.news-actions > .el-button { margin: 0; }
.news-page :deep(.el-button) { min-height: 35px; }
.connection-notice,.job-result { display: flex; align-items: center; gap: 12px; padding: 10px 13px; border: 1px solid var(--line); border-radius: 5px; font-size: 12px; margin-bottom: 16px; background: white; color: var(--muted); }
.connection-notice a { color: var(--accent); white-space: nowrap; }
.job-result { color: #347451; }
.job-result.failed { color: #a33c32; }
.job-result .icon-button { margin-left: auto; }
.news-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 11px; margin-bottom: 17px; }
.news-search { display: flex; align-items: center; gap: 8px; width: 290px; height: 36px; padding: 0 11px; border: 1px solid var(--line); border-radius: 5px; background: white; color: var(--muted); }
.news-search input { width: 100%; min-width: 0; padding: 0; border: 0; outline: none; background: none; color: var(--ink); font-size: 12px; }
.news-search:focus-within { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
.date-range { display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 10px; border: 1px solid var(--line); border-radius: 5px; background: white; color: var(--muted); }
.date-range input { width: 109px; min-height: 28px; border: 0; background: none; color: var(--ink); font-size: 11px; }
.date-range span { color: #9aa1ab; font-size: 11px; }
.status-filter { height: 36px; padding: 0 10px; background: white; border: 1px solid var(--line); border-radius: 5px; font-size: 12px; }
.sort-note { margin-left: auto; color: var(--muted); font-size: 11px; }
.text-button { display: inline-flex; align-items: center; gap: 7px; border: 0; background: none; color: var(--muted); font-size: 12px; }
.text-button:hover { color: var(--accent); }
.filter-error { color: #a33c32; font-size: 12px; margin-bottom: 12px; }
.news-results { min-height: 100px; }
.news-table { border: 1px solid var(--line); border-radius: 6px; background: white; overflow: hidden; }
.news-table-head,.news-row { display: grid; grid-template-columns: 45px minmax(0,1fr) 105px 128px 17px; gap: 16px; align-items: center; padding: 0 20px; }
.news-table-head { min-height: 37px; background: #fafbfc; border-bottom: 1px solid var(--line); font-size: 11px; color: var(--muted); }
.news-row { min-height: 55px; border-bottom: 1px solid #eef0f3; }
.news-row:last-child { border: 0; }
.news-row:hover { background: #f8faff; }
.news-row h2 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; font-weight: 550; line-height: 1.7; }
.news-row:hover h2 { color: var(--accent); }
.row-number,.row-time,.page-number { font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace; font-variant-numeric: tabular-nums; }
.row-number { font-size: 11px; color: #808995; }
.row-time { font-size: 11px; color: var(--muted); }
.summary-state { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #818995; white-space: nowrap; }
.summary-state.ready { color: #347451; }
.summary-state.retrying { color: #a56c32; }
.summary-state .el-icon { font-size: 12px; }
.row-arrow { color: #a3abb7; font-size: 12px; }
.news-pagination { display: flex; justify-content: space-between; align-items: center; gap: 15px; margin-top: 18px; color: var(--muted); font-size: 11px; }
.news-pagination > div { display: flex; align-items: center; gap: 10px; }
.news-pagination :deep(.el-button) { min-height: 29px; height: 29px; padding: 4px 8px; font-size: 11px; margin: 0; }
.news-empty { padding: 65px 20px; text-align: center; border: 1px solid var(--line); border-radius: 6px; background: white; }
.news-empty h2 { font-size: 17px; font-weight: 550; }
.news-empty p { margin: 9px 0 20px; font-size: 12px; color: var(--muted); line-height: 1.8; }
.news-footnote { margin-top: 24px; color: #78818c; font-size: 10px; }
.news-reader { max-width: 820px; margin: 0 auto; }
.reader-back { margin-bottom: 23px; }
.reader-sheet { min-height: 200px; padding: 36px 39px; border: 1px solid var(--line); border-radius: 6px; background: white; }
.reader-sheet .news-empty { border: 0; }
.reader-source { color: var(--muted); font-size: 11px; margin-bottom: 13px; }
.reader-sheet h1 { font-size: 29px; line-height: 1.55; letter-spacing: -.5px; font-weight: 650; }
.reader-meta { display: flex; align-items: center; gap: 19px; margin-top: 17px; padding-bottom: 23px; border-bottom: 1px solid var(--line); color: var(--muted); font-size: 11px; }
.article-label { margin: 25px 0 16px; font-size: 12px; font-weight: 600; }
.article-copy { white-space: pre-wrap; overflow-wrap: anywhere; color: #3d4650; font-size: 16px; line-height: 2; }
.reader-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; border-top: 1px solid var(--line); padding-top: 20px; margin-top: 28px; }
.reader-actions .el-icon { margin-left: 7px; }
.reader-actions small { color: #7b8390; font-size: 10px; }
.pending-summary { text-align: center; padding: 45px 15px; }
.pending-summary > .el-icon { color: #8993a2; font-size: 27px; margin-bottom: 14px; }
.pending-summary h2 { font-size: 16px; font-weight: 550; }
.pending-summary p { font-size: 12px; color: var(--muted); margin: 8px 0 20px; }
.pending-summary .single-error { color: #a33c32; margin: 17px 0 0; }
@media (max-width: 1000px) {
  .news-heading { flex-wrap: wrap; align-items: flex-start; gap: 18px; }
  .sort-note { display: none; }
  .news-search { width: 260px; }
  .news-table-head,.news-row { grid-template-columns: 33px minmax(0,1fr) 95px 115px 14px; gap: 13px; padding: 0 16px; }
}
@media (max-width: 640px) {
  .news-heading { margin-bottom: 22px; }
  .news-heading h1 { font-size: 24px; }
  .news-metrics { font-size: 11px; gap: 7px; }
  .news-actions { width: 100%; gap: 8px; flex-wrap: wrap; }
  .news-actions :deep(.el-button) { font-size: 11px; padding: 7px 9px; }
  .action-group select { min-width: 58px; padding-left: 8px; font-size: 11px; }
  .refresh-button span { display: none; }
  .news-actions > .refresh-button { margin-left: auto; }
  .news-filters { gap: 9px; margin-bottom: 14px; }
  .news-search { width: 100%; height: 37px; }
  .date-range { gap: 5px; padding: 0 8px; flex: 1; }
  .date-range input { width: 98px; font-size: 10px; }
  .status-filter { padding: 0 6px; max-width: 110px; font-size: 11px; }
  .news-table-head,.news-row { grid-template-columns: 22px minmax(0,1fr) 71px 11px; gap: 8px; padding: 0 11px; }
  .time-column { display: none; }
  .news-table-head { min-height: 34px; font-size: 10px; }
  .news-row { min-height: 66px; padding-top: 10px; padding-bottom: 10px; }
  .news-row h2 { font-size: 13px; white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.65; }
  .row-number,.summary-state { font-size: 10px; }
  .summary-state { gap: 4px; }
  .summary-state .el-icon { font-size: 10px; }
  .row-arrow { font-size: 11px; }
  .reader-back { margin-bottom: 19px; }
  .reader-sheet { padding: 25px 20px; }
  .reader-sheet h1 { font-size: 24px; }
  .reader-meta { flex-wrap: wrap; gap: 12px; padding-bottom: 20px; font-size: 10px; }
  .article-copy { font-size: 15px; }
  .reader-actions { flex-direction: column; align-items: flex-start; gap: 12px; }
}
@media (max-width: 360px) {
  .news-actions { gap: 6px; }
  .news-actions :deep(.el-button) { padding: 7px; font-size: 10px; }
  .action-group select { min-width: 49px; padding-left: 4px; font-size: 10px; }
  .date-range { width: 100%; flex: none; justify-content: space-between; }
  .date-range input { width: 43%; }
}
</style>
