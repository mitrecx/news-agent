import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue') },
    {
      path: '/',
      component: () => import('@/components/AppShell.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', component: () => import('@/views/HotSearchView.vue') },
        { path: 'chat', component: () => import('@/views/ChatView.vue') },
        {
          path: 'settings',
          component: () => import('@/views/SettingsView.vue'),
        },
      ],
    },
    { path: '/hot-search', redirect: '/' },
    { path: '/weibo-login', redirect: '/settings?tab=weibo' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login'
  if (to.path === '/login' && auth.isAuthenticated) return '/'
})
export default router
