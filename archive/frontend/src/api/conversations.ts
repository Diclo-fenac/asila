import { apiClient } from './client'

export interface Conversation {
  id: string
  title: string
  created_at: string
}

export async function getConversations(): Promise<Conversation[]> {
  const response = await apiClient.get<Conversation[]>('/conversations')
  return response.data
}

export async function createConversation(): Promise<Conversation> {
  const response = await apiClient.post<Conversation>('/conversations')
  return response.data
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`/conversations/${id}`)
}

export async function renameConversation(id: string, title: string): Promise<Conversation> {
  const response = await apiClient.patch<Conversation>(`/conversations/${id}`, { title })
  return response.data
}
