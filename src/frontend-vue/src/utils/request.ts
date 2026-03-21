import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

/** Create axios instance with base configuration */
const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000, // 60秒 - 一般请求的超时时间
  headers: {
    'Content-Type': 'application/json',
  },
})

/** Request interceptor - add auth token */
request.interceptors.request.use(
  (config) => {
    // Dynamically import store to avoid circular dependency
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/** Response interceptor - handle errors */
request.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status
      const message = (error.response.data as any)?.detail || '请求失败'

      switch (status) {
        case 401:
          ElMessage.error('未授权，请重新登录')
          localStorage.removeItem('auth_token')
          // Redirect to login page
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          break
        case 403:
          ElMessage.error('没有权限访问')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(message)
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

export default request
