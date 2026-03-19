import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/hot-search',
      component: () => import('@/views/HotSearchView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/weibo-manage',
      component: () => import('@/views/WeiboManageView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// Navigation guard for authentication
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
