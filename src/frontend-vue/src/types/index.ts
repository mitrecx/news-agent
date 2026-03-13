/** User type */
export interface User {
  id: number
  username: string
  email?: string
  created_at: string
}

/** Login request */
export interface LoginRequest {
  username: string
  password: string
}

/** Login response */
export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

/** Chat message */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Chat request */
export interface ChatRequest {
  message: string
  history?: ChatMessage[]
}

/** Chat response */
export interface ChatResponse {
  response: string
}

/** Health response */
export interface HealthResponse {
  status: string
  agent_ready: boolean
}

/** SSE data chunk */
export interface SSEChunk {
  content?: string
  error?: string
}
