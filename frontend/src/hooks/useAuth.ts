import { useCallback } from 'react'
import { useAuthStore } from '../store/useAuthStore'
import { login as apiLogin, signUp as apiSignUp } from '../api/auth'
import type { LoginFormData, SignUpFormData } from '../utils/validators'
import { useToast } from './useToast'

export function useAuth() {
  const { setAuth, clearAuth, setLoading, isLoading } = useAuthStore()
  const { addToast } = useToast()

  const login = useCallback(async (data: LoginFormData & { tenant_id: string }) => {
    setLoading(true)
    try {
      const result = await apiLogin({
        email: data.email,
        password: data.password,
        tenant_id: data.tenant_id,
      })

      setAuth({
        user: result.user,
        tenant: { id: data.tenant_id, name: 'Tenant' },
        access_token: result.access_token,
        refresh_token: result.refresh_token,
      })

      return { success: true as const }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Login failed'
          : 'Login failed'
      addToast(message, 'error')
      return { success: false as const, error: message }
    } finally {
      setLoading(false)
    }
  }, [setAuth, setLoading])

  const signUp = useCallback(async (data: SignUpFormData & { tenant_id: string }) => {
    setLoading(true)
    try {
      await apiSignUp({
        name: data.name,
        email: data.email,
        password: data.password,
        tenant_id: data.tenant_id,
      })
      addToast('Account created successfully', 'success')
      return { success: true as const }
    } catch (error: unknown) {
      const message =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Sign up failed'
          : 'Sign up failed'
      addToast(message, 'error')
      return { success: false as const, error: message }
    } finally {
      setLoading(false)
    }
  }, [setLoading])

  const logout = useCallback(() => {
    clearAuth()
  }, [clearAuth])

  return { login, signUp, logout, isLoading }
}
