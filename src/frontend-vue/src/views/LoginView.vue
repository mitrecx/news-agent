<template>
  <div class="login-page">
    <section class="login-story">
      <RouterLink to="/" class="login-brand"
        ><span class="brand-mark">n<span>.</span></span
        >News Agent</RouterLink
      >
      <div class="login-thesis">
        <span class="eyebrow">A CLEARER VIEW OF THE WORLD</span>
        <h1>热点之外，<br />看见更多。</h1>
        <p>收集值得关注的新闻，<br />用 AI 整理信息，也保留自己的思考。</p>
        <span class="story-line" /><small>你的新闻工作台</small>
      </div>
      <footer>STAY CURIOUS. STAY INFORMED.</footer>
    </section>
    <section class="login-form-side">
      <div class="login-form-card">
        <span class="eyebrow">WELCOME BACK</span>
        <h2>欢迎回来</h2>
        <p>登录，继续探索今天的热点。</p>
        <el-form :model="form" @submit.prevent="login"
          ><label class="field-label" for="login-username">用户名</label
          ><el-input
            id="login-username"
            v-model="form.username"
            placeholder="输入用户名"
            autocomplete="username"
            @keyup.enter="login" /><label class="field-label" for="login-password">密码</label
          ><el-input
            id="login-password"
            v-model="form.password"
            type="password"
            placeholder="输入密码"
            autocomplete="current-password"
            show-password
            @keyup.enter="login" /><el-button
            type="primary"
            @click="login"
            :loading="auth.isLoading"
            :disabled="!form.username || !form.password"
            >登录工作台 <el-icon><ArrowRight /></el-icon></el-button></el-form
        ><small class="login-footnote"
          ><el-icon><Lock /></el-icon>连接世界，也保护你的信息。</small
        >
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, ArrowRight } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const router = useRouter()
const form = reactive({ username: '', password: '' })
const login = async () => {
  if (!form.username || !form.password || auth.isLoading) return
  if (await auth.login(form.username, form.password)) router.push('/')
  else ElMessage.error('用户名或密码错误')
}
</script>
<style scoped>
.login-page {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #fff;
}
.login-story {
  background: #e9f0ee;
  padding: 45px 55px;
  display: flex;
  flex-direction: column;
}
.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 650;
  font-size: 17px;
  color: #3a5d55;
}
.login-thesis {
  margin: auto 0;
  padding: 60px 0;
}
.login-thesis .eyebrow {
  color: #89a599;
  font-size: 9px;
}
.login-thesis h1 {
  font-size: clamp(40px, 5vw, 64px);
  color: #396457;
  font-weight: 500;
  line-height: 1.7;
  letter-spacing: -2px;
  margin-top: 23px;
}
.login-thesis p {
  color: #8caa9e;
  font-size: 13px;
  line-height: 2.5;
  margin-top: 22px;
}
.story-line {
  display: block;
  background: #a0bda8;
  width: 35px;
  height: 2px;
  margin: 35px 0 22px;
}
.login-thesis > small {
  color: #90a99f;
  font-size: 11px;
}
.login-story footer {
  color: #9db0a7;
  font-size: 9px;
  letter-spacing: 2px;
}
.login-form-side {
  display: grid;
  place-items: center;
  padding: 50px;
}
.login-form-card {
  width: 100%;
  max-width: 340px;
}
.login-form-card h2 {
  font-size: 30px;
  color: #455f67;
  margin-top: 16px;
  font-weight: 550;
}
.login-form-card > p {
  color: #a2afb6;
  font-size: 12px;
  margin-top: 12px;
}
.login-form-card form {
  margin-top: 40px;
}
.login-form-card :deep(.el-input__wrapper) {
  height: 43px;
  box-shadow: 0 0 0 1px #e2e9ec inset;
}
.login-form-card .el-input {
  margin-bottom: 25px;
}
.login-form-card .el-button {
  width: 100%;
  height: 44px;
  margin-top: 8px;
  justify-content: space-between;
}
.login-form-card .el-button :deep(span) {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.login-footnote {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  color: #b4c0c4;
  margin-top: 26px;
}
@media (max-width: 760px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .login-story {
    padding: 25px;
  }
  .login-thesis {
    padding: 35px 0;
  }
  .login-thesis h1 {
    font-size: 35px;
    line-height: 1.5;
  }
  .login-thesis p {
    margin-top: 15px;
  }
  .story-line,
  .login-thesis > small,
  .login-story footer {
    display: none;
  }
  .login-form-side {
    padding: 40px 30px;
  }
  .login-brand {
    font-size: 15px;
  }
}
</style>
