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
  conversation_id?: number
}

/** Chat response */
export interface ChatResponse {
  response: string
  conversation_id?: number
}

/** Conversation types */
export interface Conversation {
  id: number
  user_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface MessageInDB {
  id: number
  conversation_id: number
  role: string
  content: string
  created_at: string
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
