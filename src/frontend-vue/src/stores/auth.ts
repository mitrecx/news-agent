import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore(
  'auth',
  () => {
    /** State */
    const token = ref<string | null>(localStorage.getItem('auth_token'))
    const user = ref<User | null>(null)
    const isLoading = ref(false)

    /** Computed */
    const isAuthenticated = computed(() => !!token.value)

    /** Actions */
    const login = async (username: string, password: string) => {
      isLoading.value = true
      try {
        const response = await authApi.login({ username, password })
        token.value = response.data.access_token
        user.value = response.data.user
        localStorage.setItem('auth_token', response.data.access_token)
        return true
      } catch (error) {
        return false
      } finally {
        isLoading.value = false
      }
    }

    const register = async (username: string, password: string, email?: string) => {
      isLoading.value = true
      try {
        const response = await authApi.register({ username, password, email })
        token.value = response.data.access_token
        user.value = response.data.user
        localStorage.setItem('auth_token', response.data.access_token)
        return true
      } catch (error) {
        return false
      } finally {
        isLoading.value = false
      }
    }

    const fetchUser = async () => {
      if (!token.value) return

      try {
        const response = await authApi.getCurrentUser()
        user.value = response.data
      } catch (error) {
        // Token might be invalid
        logout()
      }
    }

    const logout = () => {
      token.value = null
      user.value = null
      localStorage.removeItem('auth_token')
    }

    return {
      token,
      user,
      isLoading,
      isAuthenticated,
      login,
      register,
      fetchUser,
      logout,
    }
  },
  {
    persist: true,
  }
)
