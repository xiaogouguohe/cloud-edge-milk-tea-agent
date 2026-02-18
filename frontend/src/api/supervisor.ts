import axios from 'axios'

const API_BASE = '/api'

export interface ChatRequest {
  message: string
  user_id: string
  chat_id?: string
}

export interface ChatResponse {
  reply: string
  session_id: string
  role?: string
}

export const chat = async (params: ChatRequest): Promise<ChatResponse> => {
  const { data } = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
    message: params.message,
    user_id: params.user_id,
    chat_id: params.chat_id ?? 'default',
  })
  return data
}

export const clearSession = async (
  userId: string,
  chatId: string = 'default'
): Promise<{ status: string; message: string }> => {
  const { data } = await axios.post(`${API_BASE}/clear`, null, {
    params: { user_id: userId, chat_id: chatId },
  })
  return data
}

export const healthCheck = async (): Promise<{ status: string }> => {
  const { data } = await axios.get<{ status: string }>(`${API_BASE}/health`)
  return data
}
