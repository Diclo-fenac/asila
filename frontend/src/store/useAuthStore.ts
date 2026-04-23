import { create } from 'zustand'
import type { User } from '../types/auth'

interface AuthState {
  user: User | null
  tenant: { id: string; name: string } | null
  access_token: string | null
  refresh_token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setAuth: (data: { user: User; tenant: { id: string; name: string }; access_token: string; refresh_token: string }) => void
  clearAuth: () => void
  setLoading: (loading: boolean) => void
}

// Selectors — stable references to prevent re-renders
export const selectUser = (state: AuthState) => state.user
export const selectTenant = (state: AuthState) => state.tenant
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated
export const selectIsLoading = (state: AuthState) => state.isLoading

function persistAuth(state: Pick<AuthState, 'user' | 'tenant' | 'access_token' | 'refresh_token'>) {
  if (state.access_token) {
    localStorage.setItem('aasila_auth', JSON.stringify(state))
  } else {
    localStorage.removeItem('aasila_auth')
  }
}

function hydrateAuth(): Pick<AuthState, 'user' | 'tenant' | 'access_token' | 'refresh_token'> {
  try {
    const stored = localStorage.getItem('aasila_auth')
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        user: parsed.user ?? null,
        tenant: parsed.tenant ?? null,
        access_token: parsed.access_token ?? null,
        refresh_token: parsed.refresh_token ?? null,
      }
    }
  } catch {
    localStorage.removeItem('aasila_auth')
  }
  return { user: null, tenant: null, access_token: null, refresh_token: null }
}

const initial = hydrateAuth()

export const useAuthStore = create<AuthState>((set) => ({
  user: initial.user,
  tenant: initial.tenant,
  access_token: initial.access_token,
  refresh_token: initial.refresh_token,
  isAuthenticated: !!initial.access_token,
  isLoading: false,

  setAuth: ({ user, tenant, access_token, refresh_token }) => {
    const state = { user, tenant, access_token, refresh_token }
    persistAuth(state)
    set({ ...state, isAuthenticated: true, isLoading: false })
  },

  clearAuth: () => {
    localStorage.removeItem('aasila_auth')
    set({ user: null, tenant: null, access_token: null, refresh_token: null, isAuthenticated: false, isLoading: false })
  },

  setLoading: (isLoading) => set({ isLoading }),
}))
