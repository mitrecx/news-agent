import { onMounted, onUnmounted } from 'vue'
import { healthCheck } from '@/api/chat'
import { useChatStore } from '@/stores/chat'

export function useHealthCheck(interval = 30000) {
  const chatStore = useChatStore()
  let timer: number | null = null

  /** Check health status */
  const checkHealth = async () => {
    try {
      const response = await healthCheck()
      chatStore.setConnected(response.data.agent_ready)
    } catch (error) {
      chatStore.setConnected(false)
    }
  }

  /** Start health check */
  const startHealthCheck = () => {
    checkHealth()
    timer = window.setInterval(checkHealth, interval)
  }

  /** Stop health check */
  const stopHealthCheck = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onMounted(() => {
    startHealthCheck()
  })

  onUnmounted(() => {
    stopHealthCheck()
  })

  return {
    checkHealth,
    startHealthCheck,
    stopHealthCheck,
  }
}
