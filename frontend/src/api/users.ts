import { apiClient } from './client'
import type { User, UserRole } from '../types/auth'
import type { PaginatedResponse, PaginationParams } from '../types/api'

export async function fetchUsers(params?: PaginationParams): Promise<PaginatedResponse<User>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by)
  if (params?.sort_order) searchParams.set('sort_order', params.sort_order)

  const response = await apiClient.get<PaginatedResponse<User>>(`/users?${searchParams}`)
  return response.data
}

export async function inviteUser(email: string, role: UserRole, name: string): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>('/users/invite', { email, role, name })
  return response.data
}

export async function updateUserRole(userId: string, role: UserRole): Promise<User> {
  const response = await apiClient.patch<User>(`/users/${userId}/role`, { role })
  return response.data
}

export async function deleteUser(userId: string): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/users/${userId}`)
  return response.data
}
