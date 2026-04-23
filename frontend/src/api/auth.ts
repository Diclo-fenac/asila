import { apiClient } from './client'
import type {
  LoginRequest,
  SignUpRequest,
  TokenResponse,
  User,
} from '../types/auth'
import type { Tenant } from '../types/tenant'

export async function login(data: LoginRequest): Promise<TokenResponse & { user: User }> {
  const response = await apiClient.post<TokenResponse & { user: User }>('/auth/login', data)
  return response.data
}

export async function signUp(data: SignUpRequest): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>('/auth/register', data)
  return response.data
}

export async function refreshToken(refreshToken: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  return response.data
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}

export async function fetchTenants(): Promise<Tenant[]> {
  const response = await apiClient.get<Tenant[]>('/tenants')
  return response.data
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    // Always clear local storage even if the API call fails
    localStorage.removeItem('aasila_auth')
  }
}
