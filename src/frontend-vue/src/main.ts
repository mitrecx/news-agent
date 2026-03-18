import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

// Prevent multiple app instances in development (HMR issue)
const appElement = document.querySelector('#app') as HTMLElement & { __vue_app__?: unknown }
if (appElement && !appElement.__vue_app__) {
  const app = createApp(App)

  // Create pinia instance with persist plugin
  const pinia = createPinia()
  pinia.use(piniaPluginPersistedstate)

  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)

  // Register all icons
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.mount('#app')
  console.log('[main.ts] ✅ Vue app mounted')
} else {
  console.warn('[main.ts] ⚠️ App already mounted, skipping duplicate mount')
}
