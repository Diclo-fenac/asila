import { apiClient } from './client'
import { useAuthStore } from '../store/useAuthStore'
import type {
  LoginRequest,
  SignUpRequest,
  User,
} from '../types/auth'
interface AuthResponse {
  msg: string
  user: User
  tenant: { id: string }
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', data, {
    headers: {
      'X-Tenant-Id': data.tenant_id,
    },
  })
  return response.data
}

export async function signUp(data: SignUpRequest): Promise<{ msg: string }> {
  const response = await apiClient.post<{ msg: string }>('/auth/register', data, {
    headers: {
      'X-Tenant-Id': data.tenant_id,
    },
  })
  return response.data
}


export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    // Ensure frontend state is cleared regardless of API success
    useAuthStore.getState().clearAuth()
  }
}
