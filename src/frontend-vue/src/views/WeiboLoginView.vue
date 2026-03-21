<template>
  <div class="weibo-login-view">
    <AppNav :full-width="true" />

    <div class="login-container">
      <el-card class="login-card">
        <template #header>
          <div class="card-header">
            <el-icon class="header-icon"><Platform /></el-icon>
            <h2>微博登录自动化</h2>
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

        <!-- 登录方式选择 -->
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="手动输入 Cookie（推荐）" name="input">
            <div class="manual-input-container">
              <el-alert
                type="success"
                :closable="false"
                show-icon
                style="margin-bottom: 20px"
              >
                <template #title>
                  🚀 快速获取 Cookie（推荐）
                </template>
                <div>
                  <p><strong>只需 3 步，轻松获取 Cookie：</strong></p>
                  <ol style="margin-left: 20px; line-height: 1.8; margin-top: 10px;">
                    <li>点击下方"打开微博登录"按钮，在新标签页登录微博</li>
                    <li>登录成功后，按 <kbd>F12</kbd> 打开浏览器控制台</li>
                    <li>复制下方脚本代码，粘贴到控制台并按回车，Cookie 会自动复制到剪贴板</li>
                  </ol>
                </div>
              </el-alert>

              <!-- 快速操作按钮 -->
              <div class="quick-actions">
                <el-button
                  type="primary"
                  @click="openWeiboLogin"
                  size="large"
                  style="width: 100%; margin-bottom: 15px;"
                >
                  <el-icon><Connection /></el-icon>
                  打开微博登录
                </el-button>

                <el-button
                  type="success"
                  @click="copyExtractScript"
                  size="large"
                  plain
                  style="width: 100%; margin-bottom: 15px;"
                >
                  <el-icon><DocumentCopy /></el-icon>
                  复制 Cookie 提取脚本
                </el-button>

                <el-button
                  type="warning"
                  @click="addBookmarklet"
                  size="large"
                  plain
                  style="width: 100%;"
                >
                  <el-icon><Star /></el-icon>
                  添加一键提取书签（推荐）
                </el-button>
              </div>

              <el-divider />

              <!-- Cookie 提取脚本 -->
              <div class="script-section">
                <el-text tag="label" size="small" style="font-weight: bold;">
                  Cookie 提取脚本（登录成功后在控制台运行）：
                </el-text>
                <el-input
                  :model-value="extractScript"
                  type="textarea"
                  :rows="6"
                  readonly
                  class="script-textarea"
                  style="margin-top: 10px; font-family: 'Courier New', monospace; font-size: 12px;"
                />
              </div>

              <el-divider />

              <!-- 手动输入区域 -->
              <el-form label-width="100px">
                <el-form-item label="Cookie">
                  <el-input
                    v-model="manualCookie"
                    type="textarea"
                    :rows="4"
                    placeholder="或者直接粘贴微博 Cookie，格式：SUB=xxx; SUBP=xxx"
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    @click="saveManualCookie"
                    :loading="saving"
                    :disabled="!manualCookie"
                    size="large"
                    style="width: 100%"
                  >
                    <el-icon><Check /></el-icon>
                    {{ saving ? '保存中...' : '保存 Cookie' }}
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="自动登录" name="auto">
            <el-alert
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 20px"
            >
              自动登录功能可能因微博验证码、滑块验证等安全措施而失败。建议使用手动登录方式。
            </el-alert>

            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              label-width="100px"
              class="login-form"
              v-loading="loading"
              element-loading-text="正在登录微博..."
            >
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入微博用户名或手机号"
                  :prefix-icon="User"
                  clearable
                  :disabled="loading"
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入微博密码"
                  :prefix-icon="Lock"
                  show-password
                  :disabled="loading"
                  @keyup.enter="handleLogin"
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  @click="handleLogin"
                  :loading="loading"
                  :disabled="!loginForm.username || !loginForm.password"
                  style="width: 100%"
                  size="large"
                >
                  <el-icon v-if="!loading"><Connection /></el-icon>
                  {{ loading ? '登录中...' : '自动登录并获取 Cookie' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>

        <!-- 结果显示 -->
        <div v-if="loginResult" class="result-section">
          <el-divider />

          <el-alert
            :type="loginResult.success ? 'success' : 'error'"
            :closable="false"
            show-icon
          >
            <template #title>
              {{ loginResult.message }}
            </template>
          </el-alert>

          <!-- 成功时显示 Cookie -->
          <div v-if="loginResult.success && loginResult.cookie" class="cookie-result">
            <el-text tag="label" size="small">
              Cookie (已自动保存到 .env 文件):
            </el-text>
            <el-input
              v-model="loginResult.cookie"
              type="textarea"
              :rows="4"
              readonly
              class="cookie-textarea"
            />
            <el-button
              type="primary"
              plain
              size="small"
              @click="copyCookie"
              style="margin-top: 10px"
            >
              <el-icon><DocumentCopy /></el-icon>
              复制 Cookie
            </el-button>
          </div>

          <!-- 失败时显示错误详情 -->
          <div v-if="!loginResult.success && loginResult.error" class="error-details">
            <el-text type="danger" size="small">
              错误详情: {{ loginResult.error }}
            </el-text>
          </div>
        </div>

        <!-- 使用说明 -->
        <el-divider content-position="left">
          <el-text type="info" size="small">使用说明</el-text>
        </el-divider>

        <div class="instructions">
          <el-text size="small" type="info">
            <p>1. 输入您的微博账号和密码</p>
            <p>2. 点击"自动登录并获取 Cookie"按钮</p>
            <p>3. 系统将使用 Selenium 自动登录微博</p>
            <p>4. 登录成功后，Cookie 会自动保存到 .env 文件</p>
            <p>5. Cookie 用于绕过微博的反爬机制，获取热搜详情</p>
          </el-text>
        </div>

        <!-- 安全提示 -->
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 20px"
        >
          <template #title>
            安全提示
          </template>
          <div class="security-warning">
            <el-text size="small">
              • 您的密码仅在本地浏览器中使用，不会发送到第三方服务器<br>
              • Cookie 会自动保存到 .env 文件，请勿泄露给他人<br>
              • 建议定期更换密码和 Cookie<br>
              • 如果登录失败，请检查用户名和密码是否正确
            </el-text>
          </div>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  Platform,
  User,
  Lock,
  Connection,
  DocumentCopy,
  Check,
  Star
} from '@element-plus/icons-vue'
import AppNav from '@/components/AppNav.vue'
import request from '@/utils/request'

interface CookieStatus {
  has_cookie: boolean
  cookie_length: number
  cookie_preview: string | null
}

interface LoginResult {
  success: boolean
  cookie: string | null
  message: string
  error: string | null
}

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 状态
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('manual')
const manualCookie = ref('')
const loginFormRef = ref<FormInstance>()
const cookieStatus = ref<CookieStatus>({
  has_cookie: false,
  cookie_length: 0,
  cookie_preview: null
})
const loginResult = ref<LoginResult | null>(null)

// 微博登录 URL
const weiboLoginUrl = ref('https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)&entry=miniblog')

// Cookie 提取脚本
const extractScript = ref(`// 自动提取微博 Cookie 并复制到剪贴板
(function() {
  const cookies = document.cookie;
  const cookieObj = {};
  cookies.split('; ').forEach(cookie => {
    const [name, value] = cookie.split('=');
    if (name && value) {
      cookieObj[name] = value;
    }
  });

  const importantCookies = ['SUB', 'SUBP'];
  const cookieParts = [];
  importantCookies.forEach(name => {
    if (cookieObj[name]) {
      cookieParts.push(\`\${name}=\${cookieObj[name]}\`);
    }
  });

  if (cookieParts.length > 0) {
    const cookieString = cookieParts.join('; ');
    navigator.clipboard.writeText(cookieString).then(() => {
      console.log('✅ Cookie 已复制到剪贴板！');
      console.log('Cookie 内容:', cookieString);
      alert('✅ Cookie 已复制到剪贴板！\\n\\n请回到本页面粘贴到输入框中。');
    }).catch(err => {
      console.error('❌ 复制失败:', err);
      console.log('请手动复制以下内容:');
      console.log(cookieString);
      alert('❌ 复制失败，请查看控制台手动复制。');
    });
  } else {
    console.error('❌ 未找到 SUB 或 SUBP Cookie');
    alert('❌ 未找到必要的 Cookie，请确保已登录微博。');
  }
})();`)

// 获取 Cookie 状态
const fetchCookieStatus = async () => {
  try {
    const response = await request.get('/weibo/cookie-status')
    cookieStatus.value = response.data
  } catch (error: any) {
    console.error('获取 Cookie 状态失败:', error)
    // 不显示错误消息，静默失败
  }
}

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  loginResult.value = null

  try {
    const response = await request.post('/weibo/login', {
      username: loginForm.username,
      password: loginForm.password
    })

    loginResult.value = response.data

    if (response.data.success) {
      ElMessage.success('登录成功，Cookie 已保存')
      // 刷新 Cookie 状态
      await fetchCookieStatus()
    } else {
      ElMessage.error('登录失败: ' + response.data.message)
    }
  } catch (error: any) {
    console.error('登录失败:', error)
    const errorMessage = error.response?.data?.detail || error.message || '登录失败，请稍后重试'
    loginResult.value = {
      success: false,
      cookie: null,
      message: '登录失败',
      error: errorMessage
    }
    ElMessage.error(errorMessage)
  } finally {
    loading.value = false
  }
}

// 复制 Cookie
const copyCookie = async () => {
  if (!loginResult.value?.cookie) return

  try {
    await navigator.clipboard.writeText(loginResult.value.cookie)
    ElMessage.success('Cookie 已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 保存手动输入的 Cookie
const saveManualCookie = async () => {
  if (!manualCookie.value.trim()) {
    ElMessage.warning('请输入 Cookie')
    return
  }

  saving.value = true
  loginResult.value = null

  try {
    const response = await request.post('/weibo/manual-cookie', {
      cookie: manualCookie.value.trim()
    })
    
    loginResult.value = response.data
    
    if (response.data.success) {
      ElMessage.success('Cookie 保存成功')
      manualCookie.value = ''
      await fetchCookieStatus()
    } else {
      ElMessage.error('Cookie 保存失败: ' + response.data.message)
    }
  } catch (error: any) {
    console.error('保存 Cookie 失败:', error)
    const errorMessage = error.response?.data?.detail || error.message || '保存 Cookie 失败，请稍后重试'
    loginResult.value = {
      success: false,
      cookie: null,
      message: '保存 Cookie 失败',
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
  ElMessage.info('已在新标签页打开微博登录页面，登录成功后请使用下方脚本提取 Cookie')
}

// 复制提取脚本
const copyExtractScript = async () => {
  try {
    await navigator.clipboard.writeText(extractScript.value)
    ElMessage.success('脚本已复制到剪贴板！请在登录成功后的微博页面控制台粘贴运行')
  } catch {
    ElMessage.error('复制失败，请手动复制下方脚本代码')
  }
}

// 生成书签脚本
const generateBookmarklet = () => {
  // 获取当前页面的origin（协议+主机+端口）
  const origin = window.location.origin

  // 书签脚本代码
  const script = `(function(){
    // 提取Cookie
    const cookies = document.cookie;
    const cookieObj = {};
    cookies.split('; ').forEach(cookie => {
      const [name, value] = cookie.split('=');
      if (name && value) {
        cookieObj[name] = value;
      }
    });

    const importantCookies = ['SUB', 'SUBP'];
    const cookieParts = [];
    importantCookies.forEach(name => {
      if (cookieObj[name]) {
        cookieParts.push(name + '=' + cookieObj[name]);
      }
    });

    if (cookieParts.length === 0) {
      alert('❌ 未找到必要的 Cookie，请确保已登录微博。');
      return;
    }

    const cookieString = cookieParts.join('; ');

    // 发送到后端
    fetch('${origin}/api/weibo/manual-cookie', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ cookie: cookieString })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('✅ Cookie 已成功保存到系统！\\n\\n现在可以关闭此页面，回到系统使用了。');
      } else {
        alert('❌ Cookie 保存失败：' + data.message);
      }
    })
    .catch(error => {
      console.error('错误:', error);
      alert('❌ 保存失败：' + error.message);
    });
  })();`

  // 将脚本编码为URL安全的格式
  return 'javascript:' + encodeURIComponent(script)
}

// 添加书签
const addBookmarklet = () => {
  const bookmarklet = generateBookmarklet()

  // 创建一个临时的a标签来触发书签添加
  const link = document.createElement('a')
  link.href = bookmarklet
  link.innerHTML = '📋 一键提取微博Cookie'

  // 尝试添加到书签栏（需要用户手动操作）
  ElMessage({
    message: '请按以下步骤添加书签：\n1. 将下方按钮拖到浏览器书签栏\n2. 登录微博后点击书签即可自动提取Cookie',
    type: 'info',
    duration: 10000,
    dangerouslyUseHTMLString: true
  })

  // 显示书签按钮供用户拖拽
  const bookmarkletButton = document.createElement('div')
  bookmarkletButton.innerHTML = `
    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                background: white; padding: 30px; border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 9999;
                text-align: center; max-width: 500px;">
      <h3 style="margin: 0 0 20px 0; color: #409eff;">📋 添加书签</h3>
      <p style="margin: 0 0 20px 0; color: #606266; line-height: 1.6;">
        请将下方按钮拖到浏览器书签栏：<br>
        <small style="color: #909399;">(如果没有显示书签栏，按 Ctrl+Shift+B / Cmd+Shift+B 显示)</small>
      </p>
      <a href="${bookmarklet}"
         style="display: inline-block; padding: 10px 20px; background: #67c23a;
                color: white; text-decoration: none; border-radius: 4px;
                font-weight: bold; cursor: move; user-select: none;"
         ondragstart="event.dataTransfer.setData('text/plain', event.target.href)">
        📋 一键提取微博Cookie
      </a>
      <p style="margin: 20px 0 10px 0; color: #606266; font-size: 14px;">
        使用方法：<br>
        1. 登录微博<br>
        2. 点击书签栏中的"一键提取微博Cookie"<br>
        3. Cookie会自动保存到系统
      </p>
      <button onclick="this.parentElement.parentElement.remove()"
              style="padding: 8px 20px; background: #f56c6c; color: white;
                     border: none; border-radius: 4px; cursor: pointer;">
        关闭
      </button>
    </div>
  `
  document.body.appendChild(bookmarkletButton)
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
  max-width: 800px;
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

.login-tabs {
  margin-top: 20px;
}

.manual-login-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.iframe-container {
  width: 100%;
  height: 600px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.weibo-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.manual-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin: 10px 0;
}

.manual-input-container {
  padding: 20px;
}

.login-form {
  margin-top: 20px;
}

.result-section {
  margin-top: 20px;
}

.cookie-result {
  margin-top: 15px;
}

.cookie-textarea {
  margin-top: 10px;
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

.security-warning {
  line-height: 1.8;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.script-section {
  margin-bottom: 20px;
}

.script-textarea {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
</style>
