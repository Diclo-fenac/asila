export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  tenant_id: string
  is_active: boolean
  mfa_enabled: boolean
  last_login: string | null
  created_at: string
}

export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface LoginRequest {
  email: string
  password: string
  tenant_id: string
}

export interface SignUpRequest {
  name: string
  email: string
  password: string
  tenant_id: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export type { Tenant } from './tenant'
