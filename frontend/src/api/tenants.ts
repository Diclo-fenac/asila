import { apiClient } from './client'
import type { Tenant, CreateTenantRequest } from '../types/tenant'
import type { PaginatedResponse, PaginationParams } from '../types/api'

export async function fetchTenants(params?: PaginationParams): Promise<PaginatedResponse<Tenant>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))

  const response = await apiClient.get<PaginatedResponse<Tenant>>(`/tenants?${searchParams}`)
  return response.data
}

export async function createTenant(data: CreateTenantRequest): Promise<Tenant> {
  const response = await apiClient.post<Tenant>('/tenants', data)
  return response.data
}

export async function deleteTenant(id: string): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/tenants/${id}`)
  return response.data
}

export async function cancelProvisioning(id: string): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(`/tenants/${id}/cancel`)
  return response.data
}
