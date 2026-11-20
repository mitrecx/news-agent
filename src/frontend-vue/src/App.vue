<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // Try to fetch user info if token exists
  if (authStore.token) {
    await authStore.fetchUser()
  }
})
</script>
