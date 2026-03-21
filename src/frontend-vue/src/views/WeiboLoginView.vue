<template>
  <div class="weibo-login-view">
    <AppNav :full-width="true" />

    <div class="login-container">
      <el-card class="login-card">
        <template #header>
          <div class="card-header">
            <el-icon class="header-icon"><Platform /></el-icon>
            <h2>微博 Cookie 配置</h2>
          </div>
        </template>

        <!-- Cookie 状态 -->
        <div class="cookie-status-section">
          <el-alert
            :type="cookieStatus.has_cookie ? 'success' : 'warning'"
            :closable="false"
            show-icon
          >
            <template #title>
              <span v-if="cookieStatus.has_cookie">
                已配置微博 Cookie (长度: {{ cookieStatus.cookie_length }} 字符)
              </span>
              <span v-else>
                未配置微博 Cookie
              </span>
            </template>
          </el-alert>

          <div v-if="cookieStatus.cookie_preview" class="cookie-preview">
            <el-text type="info" size="small">
              Cookie 预览: {{ cookieStatus.cookie_preview }}
            </el-text>
          </div>
        </div>

        <!-- 获取 Cookie 说明 -->
        <div class="instructions-section">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px"
          >
            <template #title>
              📖 如何获取微博 Cookie
            </template>
            <div class="instructions-content">
              <p><strong>步骤：</strong></p>
              <ol style="margin-left: 20px; line-height: 2;">
                <li>点击下方"打开微博"按钮，在新标签页登录微博</li>
                <li>登录成功后，确保在微博首页 (weibo.com)</li>
                <li>按 <kbd>F12</kbd> 打开浏览器开发者工具</li>
                <li>切换到 <strong>Application</strong> 标签页</li>
                <li>左侧找到 <strong>Cookies</strong> → https://weibo.com</li>
                <li>找到 <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">SUB</code> 和 <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">SUBP</code></li>
                <li>分别复制它们的 Value 值，粘贴到下方输入框</li>
              </ol>
              <p style="margin-top: 10px; color: #e6a23c;">
                <strong>⚠️ 注意：</strong>SUB Cookie 可能是 HttpOnly 的（显示为锁形图标），需要手动复制 Value 值。
              </p>
            </div>
          </el-alert>

          <el-button
            type="primary"
            @click="openWeiboLogin"
            size="large"
            style="width: 100%; margin-bottom: 20px;"
          >
            <el-icon><Connection /></el-icon>
            打开微博
          </el-button>
        </div>

        <!-- Cookie 输入区域 -->
        <el-divider content-position="left">
          <el-text type="info" size="small">输入 Cookie</el-text>
        </el-divider>

        <el-form label-width="80px" label-position="top">
          <el-form-item label="SUB">
            <el-input
              v-model="subCookie"
              type="textarea"
              :rows="3"
              placeholder="粘贴 SUB Cookie 的 Value 值"
              clearable
            />
          </el-form-item>

          <el-form-item label="SUBP">
            <el-input
              v-model="subpCookie"
              type="textarea"
              :rows="3"
              placeholder="粘贴 SUBP Cookie 的 Value 值"
              clearable
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="saveCookies"
              :loading="saving"
              :disabled="!subCookie || !subpCookie"
              size="large"
              style="width: 100%"
            >
              <el-icon><Check /></el-icon>
              {{ saving ? '保存中...' : '保存 Cookie' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 结果显示 -->
        <div v-if="saveResult" class="result-section">
          <el-divider />

          <el-alert
            :type="saveResult.success ? 'success' : 'error'"
            :closable="false"
            show-icon
          >
            <template #title>
              {{ saveResult.message }}
            </template>
          </el-alert>

          <!-- 失败时显示错误详情 -->
          <div v-if="!saveResult.success && saveResult.error" class="error-details">
            <el-text type="danger" size="small">
              错误详情: {{ saveResult.error }}
            </el-text>
          </div>
        </div>

        <!-- 使用说明 -->
        <el-divider content-position="left">
          <el-text type="info" size="small">关于 Cookie</el-text>
        </el-divider>

        <div class="instructions">
          <el-text size="small" type="info">
            <p><strong>为什么需要 Cookie：</strong></p>
            <p>• 绕过微博的反爬虫机制</p>
            <p>• 获取完整的热搜详情信息</p>
            <p>• 提高数据抓取的成功率</p>
            <p style="margin-top: 10px;"><strong>安全提示：</strong></p>
            <p>• Cookie 仅用于访问微博公开数据</p>
            <p>• 不会保存您的账号密码</p>
            <p>• 建议定期更新 Cookie</p>
          </el-text>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Platform,
  Connection,
  Check
} from '@element-plus/icons-vue'
import AppNav from '@/components/AppNav.vue'
import request from '@/utils/request'

interface CookieStatus {
  has_cookie: boolean
  cookie_length: number
  cookie_preview: string | null
}

interface SaveResult {
  success: boolean
  message: string
  error: string | null
}

// 状态
const saving = ref(false)
const subCookie = ref('')
const subpCookie = ref('')
const cookieStatus = ref<CookieStatus>({
  has_cookie: false,
  cookie_length: 0,
  cookie_preview: null
})
const saveResult = ref<SaveResult | null>(null)

// 微博登录 URL
const weiboLoginUrl = ref('https://weibo.com/')

// 获取 Cookie 状态
const fetchCookieStatus = async () => {
  try {
    const response = await request.get('/weibo/cookie-status')
    cookieStatus.value = response.data
  } catch (error: any) {
    console.error('获取 Cookie 状态失败:', error)
  }
}

// 保存 Cookie
const saveCookies = async () => {
  if (!subCookie.value.trim() || !subpCookie.value.trim()) {
    ElMessage.warning('请输入完整的 SUB 和 SUBP Cookie')
    return
  }

  saving.value = true
  saveResult.value = null

  // 组合格式：SUB=xxx; SUBP=xxx
  const cookieString = `SUB=${subCookie.value.trim()}; SUBP=${subpCookie.value.trim()}`

  try {
    const response = await request.post('/weibo/manual-cookie', {
      cookie: cookieString
    })

    saveResult.value = {
      success: response.data.success,
      message: response.data.success ? 'Cookie 保存成功！' : '保存失败',
      error: response.data.success ? null : (response.data.message || '未知错误')
    }

    if (response.data.success) {
      ElMessage.success('Cookie 保存成功')
      subCookie.value = ''
      subpCookie.value = ''
      await fetchCookieStatus()
    } else {
      ElMessage.error('Cookie 保存失败: ' + (response.data.message || '未知错误'))
    }
  } catch (error: any) {
    console.error('保存 Cookie 失败:', error)
    const errorMessage = error.response?.data?.detail || error.message || '保存 Cookie 失败，请稍后重试'
    saveResult.value = {
      success: false,
      message: '保存失败',
      error: errorMessage
    }
    ElMessage.error(errorMessage)
  } finally {
    saving.value = false
  }
}

// 打开微博登录页面
const openWeiboLogin = () => {
  window.open(weiboLoginUrl.value, '_blank')
  ElMessage.info('已在新标签页打开微博，请按说明获取 Cookie')
}

// 组件挂载时获取 Cookie 状态
onMounted(() => {
  fetchCookieStatus()
})
</script>

<style scoped>
.weibo-login-view {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.login-container {
  max-width: 700px;
  margin: 40px auto;
  padding: 0 20px;
}

.login-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 24px;
  color: #409eff;
}

.cookie-status-section {
  margin-bottom: 20px;
}

.cookie-preview {
  margin-top: 10px;
  padding: 0 10px;
}

.instructions-section {
  margin-bottom: 20px;
}

.instructions-content {
  line-height: 1.8;
}

.instructions-content p {
  margin: 8px 0;
}

.instructions-content ol {
  margin: 10px 0;
}

.instructions-content code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.result-section {
  margin-top: 20px;
}

.error-details {
  margin-top: 10px;
  padding: 0 10px;
}

.instructions {
  padding: 0 10px;
}

.instructions p {
  margin: 5px 0;
  line-height: 1.6;
}
</style>
