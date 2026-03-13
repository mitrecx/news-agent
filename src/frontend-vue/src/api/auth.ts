import request from '@/utils/request'
import type { LoginRequest, LoginResponse, User } from '@/types'

/** Login API */
export const login = (data: LoginRequest) => {
  return request.post<LoginResponse>('/auth/login', data)
}

/** Register API */
export const register = (data: { username: string; password: string; email?: string }) => {
  return request.post<{ access_token: string; token_type: string; user: User }>(
    '/auth/register',
    data
  )
}

/** Get current user info */
export const getCurrentUser = () => {
  return request.get<User>('/auth/me')
}
