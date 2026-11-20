<template>
  <div class="settings-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">MAKE IT YOURS</span>
        <h1>设置</h1>
        <p>管理你的模型和数据源，选择适合当下任务的连接。</p>
      </div>
      <span class="personal-label"
        ><el-icon><User /></el-icon>个人工作空间</span
      >
    </div>
    <div class="settings-tabs" role="tablist" aria-label="设置分类">
      <button
        role="tab"
        :aria-selected="activeTab === 'model'"
        :class="{ active: activeTab === 'model' }"
        @click="setTab('model')"
      >
        <el-icon><Cpu /></el-icon>模型配置<span class="profile-count">{{
          store.profiles.items.length
        }}</span>
      </button>
      <button
        role="tab"
        :aria-selected="activeTab === 'weibo'"
        :class="{ active: activeTab === 'weibo' }"
        @click="setTab('weibo')"
      >
        <el-icon><Connection /></el-icon>微博连接<span
          class="tab-dot"
          :class="{ connected: store.cookieReady }"
        />
      </button>
    </div>
    <div v-if="loadError" class="surface load-error">
      <p>{{ loadError }}</p>
      <el-button @click="load">重新加载</el-button>
    </div>
    <div v-else-if="activeTab === 'model'" class="model-library" v-loading="loading">
      <section class="active-model-banner" aria-label="当前生效模型">
        <span class="active-model-symbol"
          ><el-icon><Cpu /></el-icon
        ></span>
        <div v-if="store.model" class="active-model-copy">
          <span class="active-eyebrow"><i class="status-dot" />当前使用</span>
          <h2>{{ store.model.name }}</h2>
          <p>{{ store.model.model }}<span>·</span>智能对话与手动摘要</p>
        </div>
        <div v-else class="active-model-copy">
          <span class="active-eyebrow">尚未选择模型</span>
          <h2>添加你的第一个模型</h2>
          <p>保存后自动启用，即可开始对话和生成摘要。</p>
        </div>
        <div class="active-model-note">
          <el-icon><Lock /></el-icon><span>模型配置仅你可见<br />切换后，下次请求立即生效</span>
        </div>
      </section>
      <div class="library-heading">
        <div>
          <h2>
            我的模型 <span>{{ store.profiles.items.length }}</span>
          </h2>
          <p>可以添加多个连接，每次使用其中一个。</p>
        </div>
        <el-button type="primary" :icon="Plus" :disabled="busy" @click="openCreate"
          >添加模型</el-button
        >
      </div>
      <div v-if="!store.profiles.items.length && !loading" class="surface models-empty">
        <span class="empty-model-icon"
          ><el-icon><Connection /></el-icon
        ></span>
        <h3>把常用模型放在这里</h3>
        <p>添加服务地址、API Key 和模型名称，<br />以后只需点击「启用」即可切换。</p>
        <el-button :icon="Plus" @click="openCreate">添加第一个模型</el-button>
      </div>
      <div v-else class="profile-grid">
        <article
          v-for="profile in store.profiles.items"
          :key="profile.id"
          class="surface profile-card"
          :class="{ 'profile-active': profile.is_active }"
          :aria-label="`模型 ${profile.name}`"
        >
          <div class="profile-top">
            <span class="profile-symbol"
              ><el-icon><Cpu /></el-icon></span
            ><span v-if="profile.is_active" class="pill"
              ><el-icon><CircleCheck /></el-icon>当前使用</span
            ><span v-else class="pill pill-neutral">备用</span>
          </div>
          <h3>{{ profile.name }}</h3>
          <p class="profile-model-id">{{ profile.model }}</p>
          <dl class="profile-parameters">
            <div>
              <dt>创造性</dt>
              <dd>{{ profile.temperature.toFixed(1) }}</dd>
            </div>
            <div>
              <dt>输出上限</dt>
              <dd>{{ profile.max_tokens.toLocaleString() }} <small>tokens</small></dd>
            </div>
            <div>
              <dt>API Key</dt>
              <dd class="saved-key">
                <el-icon><Lock /></el-icon>已保存
              </dd>
            </div>
          </dl>
          <div
            v-if="testResults[profile.id]"
            class="connection-result profile-result"
            :class="testResults[profile.id]!.success ? 'is-success' : 'is-error'"
            role="status"
          >
            <el-icon
              ><CircleCheck v-if="testResults[profile.id]!.success" /><Warning v-else /></el-icon
            >{{ testResults[profile.id]!.message
            }}<span v-if="testResults[profile.id]!.latency_ms"
              >{{ (testResults[profile.id]!.latency_ms! / 1000).toFixed(2) }}s</span
            >
          </div>
          <footer class="profile-actions">
            <el-button
              v-if="!profile.is_active"
              type="primary"
              :disabled="busy"
              :loading="activating === profile.id"
              @click="activate(profile)"
              >启用</el-button
            ><span v-else class="active-caption"><i class="status-dot" />正在为你工作</span>
            <div class="profile-tools">
              <button
                :aria-label="`测试 ${profile.name}`"
                :disabled="busy"
                @click="testSaved(profile)"
              >
                {{ testingId === profile.id ? '测试中…' : '测试连接' }}</button
              ><button
                class="icon-button"
                :aria-label="`编辑 ${profile.name}`"
                title="编辑模型"
                :disabled="busy"
                @click="openEdit(profile)"
              >
                <el-icon><Edit /></el-icon></button
              ><button
                class="icon-button"
                :aria-label="`删除 ${profile.name}`"
                :title="
                  profile.is_active && store.profiles.items.length > 1
                    ? '请先启用另一个模型'
                    : '删除模型'
                "
                :disabled="busy || (profile.is_active && store.profiles.items.length > 1)"
                @click="remove(profile)"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </footer>
        </article>
        <button class="add-profile-card" :disabled="busy" @click="openCreate">
          <span
            ><el-icon><Plus /></el-icon></span
          ><strong>添加另一个模型</strong><small>不同服务商，随时切换</small>
        </button>
      </div>
      <div class="model-library-footnote">
        <el-icon><InfoFilled /></el-icon
        >新增备用模型不会改变当前选择。正在进行的请求会继续使用原模型。
      </div>
    </div>
    <div v-else class="settings-grid">
      <section class="surface config-card">
        <header class="card-heading">
          <span class="setting-symbol warm"
            ><el-icon><Connection /></el-icon
          ></span>
          <div>
            <h2>微博连接</h2>
            <p>连接微博账号，用于获取热搜正文和生成摘要。</p>
          </div>
          <span class="pill" :class="{ 'pill-neutral': !store.cookieReady }">{{
            store.cookieReady ? '已配置' : '待连接'
          }}</span>
        </header>
        <div class="cookie-notice">
          <el-icon><Lock /></el-icon>微博 Cookie
          作为当前工作台的共享数据源凭据，仅用于采集。保存后立即生效。
        </div>
        <ol class="cookie-steps">
          <li>
            <span>1</span>
            <div>
              <strong>在浏览器登录微博</strong>
              <p>在微博中完成登录，并打开一个热搜详情页。</p>
              <a href="https://s.weibo.com/" target="_blank" rel="noopener noreferrer"
                >打开微博 ↗</a
              >
            </div>
          </li>
          <li>
            <span>2</span>
            <div>
              <strong>复制 Cookie</strong>
              <p>
                打开开发者工具 → Network，选中微博请求，复制请求头中的 Cookie。也可以在 Application
                中复制 SUB 和 SUBP。
              </p>
            </div>
          </li>
          <li>
            <span>3</span>
            <div>
              <strong>粘贴并保存</strong>
              <p>支持完整 Cookie 字符串：SUB=…; SUBP=…</p>
            </div>
          </li>
        </ol>
        <form class="cookie-form" @submit.prevent="saveCookie">
          <label class="field-label" for="weibo-cookie">微博 Cookie</label
          ><el-input
            id="weibo-cookie"
            v-model="cookie"
            type="password"
            autocomplete="new-password"
            placeholder="粘贴 Cookie，不会回显已保存的值"
          />
          <p class="field-help">更新时覆盖原有凭据。Cookie 失效后，重新登录微博获取。</p>
          <div
            v-if="cookieMessage"
            class="connection-result"
            :class="cookieSuccess ? 'is-success' : 'is-error'"
            role="status"
          >
            {{ cookieMessage }}
          </div>
          <footer class="form-footer">
            <span class="field-help">保存后即可回到热点资讯生成摘要</span
            ><el-button
              type="primary"
              @click="saveCookie"
              :loading="savingCookie"
              :disabled="!cookie.trim()"
              >保存连接</el-button
            >
          </footer>
        </form>
      </section>
      <aside class="settings-aside">
        <section class="surface active-config">
          <span class="eyebrow">DATA SOURCE</span
          ><span class="aside-icon warm"
            ><el-icon><TrendCharts /></el-icon
          ></span>
          <h3>微博热搜</h3>
          <span class="pill" :class="{ 'pill-neutral': !store.cookieReady }">{{
            store.cookieReady ? '已配置 Cookie' : '尚未配置 Cookie'
          }}</span>
          <p class="cookie-aside-text">
            热搜标题通常可以直接采集。获取完整正文时，需要有效的微博登录凭据。
          </p>
          <RouterLink to="/" class="back-to-feed">返回热点资讯 →</RouterLink>
        </section>
      </aside>
    </div>
    <el-dialog
      v-model="editorOpen"
      :title="editingId ? '编辑模型' : '添加模型'"
      width="min(600px, calc(100vw - 32px))"
      top="6vh"
      class="model-editor-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="!editorBusy"
      :show-close="!editorBusy"
      @closed="clearEditor"
    >
      <form class="model-form" novalidate @submit.prevent="save">
        <div class="field">
          <label class="field-label" for="model-display-name">显示名称 <span>*</span></label
          ><el-input
            id="model-display-name"
            v-model="form.name"
            placeholder="例如：日常助手、深度分析"
            maxlength="80"
            :disabled="editorBusy"
          />
          <p class="field-help">为这个连接取一个容易识别的名字。</p>
        </div>
        <div class="field">
          <label class="field-label" for="model-api-url">API 地址 <span>*</span></label
          ><el-input
            id="model-api-url"
            v-model="form.base_url"
            placeholder="https://api.deepseek.com/v1"
            autocomplete="off"
            :disabled="editorBusy"
            @input="clearResult"
          />
          <p class="field-help">填写服务商的 API 根地址，通常以 /v1 结尾。</p>
        </div>
        <div class="field">
          <label class="field-label" for="model-api-key"
            >API Key <span v-if="!editingId">*</span
            ><span v-else class="key-saved">已安全保存</span></label
          ><el-input
            id="model-api-key"
            v-model="form.api_key"
            type="password"
            :placeholder="editingId ? '留空保留此模型已保存的密钥' : '输入此连接的 API Key'"
            autocomplete="new-password"
            :disabled="editorBusy"
            @input="clearResult"
          />
          <p class="field-help">
            <el-icon><Lock /></el-icon>密钥加密保存在服务器，不会回显，也不会被其他模型借用。
          </p>
        </div>
        <div class="field">
          <label class="field-label" for="model-name">模型名称 <span>*</span></label>
          <div class="model-select-row">
            <el-input
              id="model-name"
              v-model="form.model"
              list="available-models"
              placeholder="填写服务商提供的模型 ID"
              :disabled="editorBusy"
              @input="clearResult"
            /><datalist id="available-models">
              <option v-for="name in availableModels" :key="name" :value="name" /></datalist
            ><el-button :loading="listing" :disabled="editorBusy" @click="fetchModels"
              >获取模型列表</el-button
            >
          </div>
          <p class="field-help">
            {{
              availableModels.length
                ? `已找到 ${availableModels.length} 个模型，可选择或手动输入。`
                : '一个连接对应一个模型，可以添加多个连接。'
            }}
          </p>
        </div>
        <div class="advanced-title"><span>生成参数</span><span>按需要调整</span></div>
        <div class="parameter-grid">
          <div>
            <label class="field-label" for="model-temperature"
              >创造性<span class="parameter-value">{{ form.temperature.toFixed(1) }}</span></label
            ><el-slider
              id="model-temperature"
              v-model="form.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :disabled="editorBusy"
              @input="clearResult"
            />
            <div class="range-labels"><span>严谨</span><span>灵活</span></div>
          </div>
          <div>
            <label class="field-label" for="model-max-tokens">最大输出长度</label
            ><el-input-number
              id="model-max-tokens"
              v-model="form.max_tokens"
              :min="64"
              :max="65536"
              :step="256"
              controls-position="right"
              :disabled="editorBusy"
            />
          </div>
        </div>
        <div
          v-if="result"
          class="connection-result"
          :class="result.success ? 'is-success' : 'is-error'"
          role="status"
        >
          <el-icon><CircleCheck v-if="result.success" /><Warning v-else /></el-icon
          >{{ result.message
          }}<span v-if="result.latency_ms">{{ (result.latency_ms / 1000).toFixed(2) }}s</span>
        </div>
        <div class="editor-note">
          <el-icon><InfoFilled /></el-icon
          >{{
            !store.profiles.items.length
              ? '第一个模型保存后自动启用。'
              : '保存后保留当前选择；你可以回到列表启用这个模型。'
          }}
        </div>
        <footer class="form-footer">
          <el-button :disabled="editorBusy" :loading="testingDraft" @click="testDraft"
            >测试连接</el-button
          ><el-button :disabled="editorBusy" @click="editorOpen = false">取消</el-button
          ><el-button type="primary" :disabled="editorBusy" :loading="saving" @click="save"
            >{{ editingId ? '保存修改' : '添加模型' }}<el-icon><ArrowRight /></el-icon
          ></el-button>
        </footer>
      </form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Cpu,
  Connection,
  Lock,
  CircleCheck,
  Warning,
  ArrowRight,
  User,
  InfoFilled,
  TrendCharts,
  Plus,
  Edit,
  Delete,
} from '@element-plus/icons-vue'
import {
  getModelProfiles,
  createModelProfile,
  updateModelProfile,
  activateModelProfile,
  deleteModelProfile,
  testSavedModel,
  testModelConnection,
  listModels,
  saveWeiboCookie,
  type ModelProfile,
  type ModelSettingsInput,
  type ConnectionResult,
} from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
const route = useRoute()
const router = useRouter()
const store = useSettingsStore()
const activeTab = computed(() => (route.query.tab === 'weibo' ? 'weibo' : 'model'))
const setTab = (tab: string) =>
  router.replace({ path: '/settings', query: tab === 'weibo' ? { tab } : {} })
const loading = ref(true)
const loadError = ref('')
const editorOpen = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  name: '',
  base_url: '',
  api_key: '',
  model: '',
  temperature: 0.7,
  max_tokens: 2000,
})
const saving = ref(false)
const testingDraft = ref(false)
const listing = ref(false)
const activating = ref('')
const deleting = ref(false)
const testingId = ref('')
const result = ref<ConnectionResult | null>(null)
const testResults = ref<Record<string, ConnectionResult>>({})
const availableModels = ref<string[]>([])
const editorBusy = computed(() => saving.value || testingDraft.value || listing.value)
const busy = computed(
  () => editorBusy.value || !!activating.value || deleting.value || !!testingId.value,
)
const cookie = ref('')
const savingCookie = ref(false)
const cookieMessage = ref('')
const cookieSuccess = ref(false)
const clearResult = () => {
  result.value = null
}
const clearEditor = () => {
  form.api_key = ''
  form.base_url = ''
  result.value = null
  availableModels.value = []
}
const errorMessage = (error: unknown) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : '请求失败，请检查连接信息后重试'
}
const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    store.profiles = (await getModelProfiles()).data
    await store.refresh()
  } catch {
    loadError.value = '模型暂时无法加载，请检查服务连接后重试。'
  } finally {
    loading.value = false
  }
}
const openCreate = () => {
  editingId.value = null
  Object.assign(form, {
    name: '',
    base_url: '',
    api_key: '',
    model: '',
    temperature: 0.7,
    max_tokens: 2000,
  })
  result.value = null
  availableModels.value = []
  editorOpen.value = true
}
const openEdit = (profile: ModelProfile) => {
  editingId.value = profile.id
  Object.assign(form, {
    name: profile.name,
    base_url: profile.base_url,
    api_key: '',
    model: profile.model,
    temperature: profile.temperature,
    max_tokens: profile.max_tokens,
  })
  result.value = null
  availableModels.value = []
  editorOpen.value = true
}
const draft = (forListing = false): ModelSettingsInput | null => {
  if (!form.base_url.trim() || (!forListing && (!form.name.trim() || !form.model.trim()))) {
    ElMessage.warning('请填写显示名称、API 地址和模型名称')
    return null
  }
  if (!editingId.value && !form.api_key.trim()) {
    ElMessage.warning('添加模型时需要填写 API Key')
    return null
  }
  return {
    name: form.name.trim() || '待保存模型',
    base_url: form.base_url.trim(),
    model: form.model.trim() || 'model-discovery',
    api_key: form.api_key.trim() || undefined,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
  }
}
const save = async () => {
  if (editorBusy.value) return
  const data = draft()
  if (!data) return
  saving.value = true
  try {
    if (editingId.value) await updateModelProfile(editingId.value, data)
    else await createModelProfile(data)
    form.api_key = ''
    await store.refreshModels()
    editorOpen.value = false
    ElMessage.success(editingId.value ? '模型修改已保存' : '模型已添加')
  } catch (error) {
    result.value = { success: false, message: errorMessage(error) }
  } finally {
    saving.value = false
  }
}
const activate = async (profile: ModelProfile) => {
  if (busy.value) return
  activating.value = profile.id
  try {
    store.profiles = (await activateModelProfile(profile.id)).data
    ElMessage.success(`已启用「${profile.name}」，下次请求生效`)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    activating.value = ''
  }
}
const remove = async (profile: ModelProfile) => {
  try {
    await ElMessageBox.confirm(
      store.profiles.items.length === 1
        ? '删除后将没有可用模型，需要重新添加才能对话和生成摘要。'
        : `确定删除模型「${profile.name}」及其保存的密钥？`,
      '删除模型',
      { confirmButtonText: '删除模型', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    store.profiles = (await deleteModelProfile(profile.id)).data
    delete testResults.value[profile.id]
    ElMessage.success('模型已删除')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    deleting.value = false
  }
}
const testSaved = async (profile: ModelProfile) => {
  if (busy.value) return
  testingId.value = profile.id
  try {
    testResults.value[profile.id] = (await testSavedModel(profile.id)).data
  } catch (error) {
    testResults.value[profile.id] = { success: false, message: errorMessage(error) }
  } finally {
    testingId.value = ''
  }
}
const testDraft = async () => {
  const data = draft()
  if (!data) return
  testingDraft.value = true
  result.value = null
  try {
    result.value = (await testModelConnection(data, editingId.value || undefined)).data
  } catch (error) {
    result.value = { success: false, message: errorMessage(error) }
  } finally {
    testingDraft.value = false
  }
}
const fetchModels = async () => {
  const data = draft(true)
  if (!data) return
  listing.value = true
  try {
    availableModels.value = (await listModels(data, editingId.value || undefined)).data.models
    if (!availableModels.value.length) ElMessage.info('服务商没有返回模型列表，请手动填写')
  } catch (error) {
    result.value = { success: false, message: errorMessage(error) }
  } finally {
    listing.value = false
  }
}
const saveCookie = async () => {
  savingCookie.value = true
  cookieMessage.value = ''
  try {
    const data = (await saveWeiboCookie(cookie.value.trim())).data
    cookieSuccess.value = data.success
    cookieMessage.value = data.message
    if (data.success) {
      cookie.value = ''
      await store.refresh()
      ElMessage.success('微博连接已保存并生效')
    }
  } catch (error) {
    cookieSuccess.value = false
    cookieMessage.value = errorMessage(error)
  } finally {
    savingCookie.value = false
  }
}
onMounted(load)
</script>
<style scoped>
.personal-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #8c9ba4;
}
.settings-tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 27px;
}
.settings-tabs button {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #8a99a3;
  padding: 0 2px 17px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
}
.settings-tabs button.active {
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 600;
}
.tab-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c2cbd1;
  margin-left: 4px;
}
.tab-dot.connected {
  background: #4fa17e;
}
.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 265px;
  gap: 24px;
  align-items: start;
}
.config-card {
  padding: 28px 30px 0;
}
.card-heading {
  display: flex;
  gap: 13px;
  align-items: center;
  padding-bottom: 24px;
  border-bottom: 1px solid #edf0f3;
}
.setting-symbol {
  width: 39px;
  height: 39px;
  display: grid;
  place-items: center;
  font-size: 20px;
  color: #448b7c;
  background: #edf6f1;
  border-radius: 10px;
  flex-shrink: 0;
}
.setting-symbol.warm {
  background: #fff2e8;
  color: #cd8f60;
}
.card-heading h2 {
  font-size: 15px;
  font-weight: 600;
}
.card-heading p {
  font-size: 10px;
  color: #95a0a9;
  margin-top: 7px;
  line-height: 1.6;
}
.card-heading .pill {
  margin-left: auto;
  font-size: 9px;
}
.default-notice {
  background: #f2f7f5;
  border: 1px solid #e5efea;
  border-radius: 8px;
  margin-top: 24px;
  padding: 14px;
  display: flex;
  gap: 9px;
  align-items: start;
  color: #5a8c7a;
}
.default-notice strong {
  font-size: 10px;
  font-weight: 500;
}
.default-notice p {
  font-size: 9px;
  color: #87a295;
  margin-top: 5px;
  line-height: 1.6;
}
.default-notice > .el-icon {
  font-size: 14px;
  margin-top: 3px;
}
.default-notice button {
  margin-left: auto;
  background: none;
  border: 0;
  color: #528c75;
  font-size: 9px;
  white-space: nowrap;
  padding-top: 4px;
}
.model-form {
  padding-top: 26px;
}
.field {
  margin-bottom: 24px;
}
.field-label > span:not(.key-saved) {
  color: #c7866e;
  margin-left: 3px;
}
.field-label .key-saved {
  margin-left: 9px;
  font-size: 9px;
  color: #6f9d86;
  font-weight: 400;
}
.field-help .el-icon {
  vertical-align: -2px;
  margin-right: 3px;
}
.field :deep(.el-input__wrapper) {
  min-height: 40px;
  box-shadow: 0 0 0 1px #e3e9ed inset;
}
.model-select-row {
  display: flex;
  gap: 9px;
}
.model-select-row .el-button {
  height: 40px;
}
.advanced-title {
  display: flex;
  justify-content: space-between;
  padding-top: 22px;
  border-top: 1px solid #edf1f3;
  font-size: 12px;
  color: #546d78;
  margin: 6px 0 22px;
}
.advanced-title span + span {
  color: #a4afb6;
  font-size: 9px;
}
.parameter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  margin-bottom: 26px;
}
.parameter-value {
  float: right;
  color: var(--accent) !important;
  font:
    11px Menlo,
    monospace;
}
.parameter-grid :deep(.el-input-number) {
  width: 100%;
}
.parameter-grid :deep(.el-slider__runway) {
  margin: 13px 0;
  height: 4px;
}
.parameter-grid :deep(.el-slider__bar) {
  height: 4px;
}
.parameter-grid :deep(.el-slider__button) {
  width: 12px;
  height: 12px;
}
.range-labels {
  display: flex;
  justify-content: space-between;
  color: #a2aeb5;
  font-size: 9px;
}
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 21px 0;
  border-top: 1px solid #edf1f3;
  margin-top: 25px;
  align-items: center;
}
.form-footer .el-button {
  height: 36px;
  padding: 0 18px;
}
.form-footer .el-icon {
  margin-left: 12px;
}
.form-footer .field-help {
  margin: 0 auto 0 0;
}
.settings-aside {
  display: grid;
  gap: 22px;
}
.active-config {
  padding: 25px;
}
.active-config .eyebrow {
  font-size: 8px;
  letter-spacing: 1.5px;
}
.aside-icon {
  margin: 24px 0 15px;
  width: 44px;
  height: 44px;
  border: 1px solid #dfeae7;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #589a88;
  background: #f5faf7;
  font-size: 24px;
}
.aside-icon.warm {
  color: #d3936e;
  background: #fbf6f1;
  border-color: #f3e7dc;
}
.active-config h3 {
  font-size: 16px;
  font-weight: 600;
  overflow-wrap: anywhere;
  margin-bottom: 12px;
}
.active-config .pill {
  font-size: 9px;
}
.active-config dl {
  margin-top: 27px;
  display: grid;
  gap: 17px;
}
.active-config dl > div {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  gap: 8px;
}
.active-config dt {
  color: #96a3ac;
}
.active-config dd {
  color: #637780;
}
.active-config > p {
  border-top: 1px solid #edf1f3;
  padding-top: 19px;
  margin-top: 24px;
  color: #9aa7af;
  font-size: 10px;
  line-height: 1.9;
}
.help-note {
  padding: 0 8px;
}
.help-note h3 {
  font-size: 11px;
  color: #7c919b;
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 500;
}
.help-note p {
  margin-top: 12px;
  color: #9ca8b0;
  font-size: 10px;
  line-height: 1.9;
}
.reset-link {
  border: 0;
  background: none;
  color: #829c9c;
  font-size: 10px;
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 22px;
}
.connection-result {
  padding: 12px;
  margin: 15px 0;
  border-radius: 7px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 7px;
  line-height: 1.6;
}
.connection-result span {
  margin-left: auto;
}
.is-success {
  background: #edf7f1;
  color: #4c9570;
}
.is-error {
  background: #fff3ee;
  color: #b87556;
}
.load-error {
  padding: 30px;
  line-height: 3;
  font-size: 12px;
}
.cookie-notice {
  color: #8c9b9f;
  font-size: 10px;
  line-height: 1.8;
  background: #f6f8f9;
  padding: 14px;
  border-radius: 8px;
  margin-top: 23px;
}
.cookie-notice .el-icon {
  vertical-align: -2px;
  margin-right: 4px;
}
.cookie-steps {
  list-style: none;
  display: grid;
  gap: 25px;
  padding: 30px 0;
}
.cookie-steps li {
  display: flex;
  align-items: start;
  gap: 15px;
}
.cookie-steps li > span {
  width: 23px;
  height: 23px;
  border-radius: 50%;
  border: 1px solid #dfe7e9;
  font-size: 10px;
  display: grid;
  place-items: center;
  color: #81979a;
  flex-shrink: 0;
}
.cookie-steps strong {
  font-size: 12px;
  font-weight: 500;
}
.cookie-steps p {
  font-size: 10px;
  line-height: 1.9;
  color: #97a4ae;
  margin-top: 6px;
}
.cookie-steps a {
  display: block;
  margin-top: 8px;
  font-size: 10px;
  color: #4a9686;
}
.cookie-form {
  border-top: 1px solid var(--line);
  padding-top: 24px;
}
.back-to-feed {
  display: inline-block;
  margin-top: 20px;
  font-size: 10px;
  color: #5d9183;
}
@media (max-width: 1150px) {
  .settings-grid {
    grid-template-columns: minmax(0, 1fr) 220px;
    gap: 18px;
  }
  .config-card {
    padding: 22px 22px 0;
  }
  .active-config {
    padding: 22px 18px;
  }
  .card-heading .pill {
    display: none;
  }
  .default-notice {
    flex-wrap: wrap;
  }
  .default-notice button {
    margin-left: 23px;
  }
  .parameter-grid {
    gap: 25px;
  }
}
@media (max-width: 950px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  .settings-aside {
    grid-template-columns: 1fr 1fr;
  }
  .active-config dl {
    margin-top: 20px;
  }
  .aside-icon {
    margin-top: 18px;
  }
  .help-note {
    padding: 16px;
  }
}
@media (max-width: 600px) {
  .config-card {
    padding: 20px 16px 0;
  }
  .personal-label {
    display: none;
  }
  .settings-aside {
    grid-template-columns: 1fr;
  }
  .model-select-row {
    flex-wrap: wrap;
  }
  .model-select-row .el-button {
    width: 100%;
  }
  .parameter-grid {
    grid-template-columns: 1fr;
    gap: 22px;
  }
  .cookie-form .form-footer {
    flex-wrap: wrap;
  }
  .settings-tabs {
    gap: 25px;
  }
  .card-heading p {
    font-size: 9px;
  }
}
</style>

<style scoped>
.field-help {
  font-size: 11px;
  color: #879aa4;
}
.card-heading p,
.help-note p,
.active-config > p {
  font-size: 11px;
}
.card-heading h2 {
  font-size: 16px;
}
.default-notice strong,
.default-notice p {
  font-size: 11px;
}
.default-notice button {
  font-size: 10px;
}
.active-config dl > div {
  font-size: 10px;
}
</style>

<style scoped>
.profile-count {
  display: inline-grid;
  place-items: center;
  min-width: 19px;
  height: 18px;
  font-size: 9px;
  border-radius: 4px;
  background: #e8f0eb;
  color: #71a08b;
}
.active-model-banner {
  display: flex;
  gap: 19px;
  align-items: center;
  background: #eaf3ee;
  border: 1px solid #dce9e1;
  padding: 25px 28px;
  border-radius: 12px;
  margin-bottom: 33px;
}
.active-model-symbol {
  width: 52px;
  height: 52px;
  border-radius: 13px;
  border: 1px solid #cfe2d7;
  background: #f6fbf8;
  color: #4e8b72;
  display: grid;
  place-items: center;
  font-size: 26px;
  flex-shrink: 0;
}
.active-eyebrow {
  display: flex;
  gap: 6px;
  align-items: center;
  color: #7a9a89;
  font-size: 10px;
}
.active-eyebrow .status-dot {
  width: 4px;
  height: 4px;
}
.active-model-copy h2 {
  margin-top: 6px;
  font-size: 19px;
  font-weight: 600;
  color: #3d6a57;
}
.active-model-copy p {
  color: #8aa797;
  margin-top: 6px;
  font-size: 11px;
  overflow-wrap: anywhere;
}
.active-model-copy p > span {
  margin: 0 10px;
}
.active-model-note {
  display: flex;
  gap: 8px;
  align-items: start;
  margin-left: auto;
  font-size: 10px;
  color: #91ab9b;
  line-height: 1.9;
}
.active-model-note .el-icon {
  margin-top: 3px;
}
.library-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 21px;
  gap: 15px;
}
.library-heading h2 {
  font-size: 15px;
  font-weight: 600;
  color: #4e6771;
}
.library-heading h2 > span {
  font-size: 11px;
  margin-left: 7px;
  color: #9badb4;
  font-weight: 400;
}
.library-heading p {
  font-size: 11px;
  color: #9aaab1;
  margin-top: 8px;
}
.library-heading .el-button {
  height: 36px;
  padding: 0 16px;
}
.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.profile-card {
  padding: 24px 25px 0;
  transition: border-color 0.15s;
}
.profile-card.profile-active {
  border-color: #9ac0ab;
  box-shadow: 0 0 0 2px #edf6f0;
}
.profile-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 21px;
}
.profile-symbol {
  width: 35px;
  height: 35px;
  display: grid;
  place-items: center;
  background: #f2f6f6;
  border-radius: 9px;
  color: #89a3a4;
  font-size: 19px;
}
.profile-active .profile-symbol {
  background: #eaf4ec;
  color: #66977b;
}
.profile-top .pill {
  font-size: 9px;
}
.profile-card h3 {
  font-size: 17px;
  font-weight: 600;
  color: #48636b;
  overflow-wrap: anywhere;
}
.profile-model-id {
  font:
    10px/1.8 Menlo,
    monospace;
  color: #9eafb4;
  margin-top: 8px;
  overflow-wrap: anywhere;
}
.profile-parameters {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr 1fr;
  gap: 12px;
  padding: 24px 0;
}
.profile-parameters dt {
  font-size: 9px;
  color: #a2b0b7;
  margin-bottom: 8px;
}
.profile-parameters dd {
  font-size: 11px;
  color: #6f8790;
}
.profile-parameters dd small {
  color: #adbac0;
  font-size: 8px;
}
.saved-key {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #7f9f8c !important;
  font-size: 10px !important;
}
.profile-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-top: 1px solid #edf1f2;
}
.profile-actions > .el-button {
  height: 29px;
  font-size: 10px;
  padding: 0 17px;
}
.active-caption {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  font-size: 10px;
  color: #79a28b;
}
.active-caption .status-dot {
  width: 4px;
  height: 4px;
}
.profile-tools {
  display: flex;
  align-items: center;
  gap: 5px;
}
.profile-tools > button:not(.icon-button) {
  border: none;
  background: none;
  color: #8da49f;
  font-size: 10px;
  padding: 6px;
}
.profile-tools > button:disabled {
  opacity: 0.45;
}
.profile-tools .icon-button {
  width: 27px;
  font-size: 14px;
}
.profile-result {
  margin: 0 0 16px;
  font-size: 10px;
}
.add-profile-card {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed #d4e1df;
  background: #f9fbfb;
  border-radius: 12px;
  color: #9bb3aa;
  gap: 12px;
}
.add-profile-card:hover {
  background: #f0f7f3;
  border-color: #aac8b7;
}
.add-profile-card > span {
  width: 39px;
  height: 39px;
  border: 1px solid #dfebe4;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 19px;
  margin-bottom: 6px;
}
.add-profile-card strong {
  font-weight: 400;
  font-size: 12px;
  color: #86a497;
}
.add-profile-card small {
  font-size: 10px;
  color: #adbeb6;
}
.model-library-footnote {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: #a0b0b6;
  margin-top: 22px;
  line-height: 1.9;
}
.models-empty {
  padding: 65px 25px;
  text-align: center;
}
.empty-model-icon {
  display: inline-grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 15px;
  background: #eef6f0;
  color: #8caf99;
  font-size: 26px;
  margin-bottom: 20px;
}
.models-empty h3 {
  font-size: 18px;
  color: #6c8d7d;
  font-weight: 500;
}
.models-empty p {
  font-size: 12px;
  color: #a4b5ab;
  line-height: 2;
  margin: 16px 0 24px;
}
.model-form {
  padding: 0 4px;
}
.editor-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: #98ada4;
}
.model-form .form-footer {
  margin-top: 20px;
  padding-bottom: 0;
}
@media (min-width: 1600px) {
  .profile-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 1050px) {
  .active-model-note {
    display: none;
  }
  .profile-card {
    padding: 22px 20px 0;
  }
  .profile-parameters {
    grid-template-columns: 1fr 1.2fr 1fr;
    gap: 8px;
  }
}
@media (max-width: 760px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
  .active-model-banner {
    padding: 22px 20px;
    gap: 13px;
  }
  .active-model-copy h2 {
    font-size: 17px;
  }
  .active-model-copy p {
    font-size: 10px;
    line-height: 1.8;
  }
  .active-model-symbol {
    width: 43px;
    height: 43px;
    font-size: 22px;
  }
  .library-heading p {
    font-size: 10px;
  }
  .add-profile-card {
    min-height: 150px;
  }
  .model-library-footnote {
    align-items: start;
  }
  .model-library-footnote .el-icon {
    margin-top: 4px;
  }
}
</style>
