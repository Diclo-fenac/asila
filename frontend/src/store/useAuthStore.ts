import { create } from 'zustand'
import type { User } from '../types/auth'

interface AuthState {
  user: User | null
  tenant: { id: string; name: string } | null
  isAuthenticated: boolean
  isLoading: boolean
  setAuth: (data: { user: User; tenant: { id: string; name: string } }) => void
  clearAuth: () => void
  setLoading: (loading: boolean) => void
}

// Selectors — stable references to prevent re-renders
export const selectUser = (state: AuthState) => state.user
export const selectTenant = (state: AuthState) => state.tenant
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated
export const selectIsLoading = (state: AuthState) => state.isLoading

function persistAuth(state: Pick<AuthState, 'user' | 'tenant'>) {
  if (state.user) {
    localStorage.setItem('aasila_auth', JSON.stringify(state))
  } else {
    localStorage.removeItem('aasila_auth')
  }
}

function hydrateAuth(): Pick<AuthState, 'user' | 'tenant'> {
  try {
    const stored = localStorage.getItem('aasila_auth')
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        user: parsed.user ?? null,
        tenant: parsed.tenant ?? null,
      }
    }
  } catch {
    localStorage.removeItem('aasila_auth')
  }
  return { user: null, tenant: null }
}

const initial = hydrateAuth()

export const useAuthStore = create<AuthState>((set) => ({
  user: initial.user,
  tenant: initial.tenant,
  isAuthenticated: !!initial.user,
  isLoading: false,

  setAuth: ({ user, tenant }) => {
    const state = { user, tenant }
    persistAuth(state)
    set({ ...state, isAuthenticated: true, isLoading: false })
  },

  clearAuth: () => {
    localStorage.removeItem('aasila_auth')
    set({ user: null, tenant: null, isAuthenticated: false, isLoading: false })
    // Hard redirect to prevent stale authenticated layouts from rendering
    if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
      window.location.href = '/login'
    }
  },

  setLoading: (isLoading) => set({ isLoading }),
}))
