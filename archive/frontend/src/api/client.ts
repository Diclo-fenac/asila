import axios, { type AxiosInstance } from 'axios'
import { useAuthStore } from '../store/useAuthStore'
import { globalToast } from '../components/ui/Toast'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export function getStoredTenantId(): string | null {
  try {
    const auth = localStorage.getItem('aasila_auth')
    if (auth) {
      const parsed = JSON.parse(auth)
      return parsed?.tenant?.id ?? null
    }
  } catch {
    return null
  }
  return null
}

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    withCredentials: true, // Crucial for HttpOnly cookies
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor: inject tenant ID and strip trailing slashes
  client.interceptors.request.use((config) => {
    const tenantId = getStoredTenantId()

    if (tenantId) {
      config.headers['X-Tenant-Id'] = tenantId
    }

    if (config.url && config.url.endsWith('/')) {
      config.url = config.url.slice(0, -1)
    }

    return config
  })

  // Response interceptor: handle 401s and silent refresh
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      // If error is 401 and we haven't already retried
      if (error.response?.status === 401 && !originalRequest._retry) {
        // Exclude auth entrypoints from refresh attempts
        if (
          originalRequest.url.includes('/auth/refresh') ||
          originalRequest.url.includes('/auth/login') ||
          originalRequest.url.includes('/auth/register')
        ) {
          if (originalRequest.url.includes('/auth/refresh')) {
            useAuthStore.getState().clearAuth()
          }
          return Promise.reject(error instanceof Error ? error : new Error(String(error)))
        }

        originalRequest._retry = true

        try {
          // Attempt to refresh the token using HttpOnly cookies
          await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true })
          
          // Retry the original request (cookies are automatically attached)
          return client(originalRequest)
        } catch (refreshError) {
          // Refresh failed, logout user
          
          // Emergency save chat draft to prevent data loss
          const chatInput = document.getElementById('chat-input') as HTMLTextAreaElement | null
          if (chatInput && chatInput.value.trim()) {
            localStorage.setItem('chat_draft_backup', chatInput.value)
          }

          useAuthStore.getState().clearAuth()
          return Promise.reject(refreshError)
        }
      }

      // If there is no response (network error) or it's a 5xx error
      if (!error.response) {
        globalToast('Network error: Unable to connect to the server.', 'error')
      } else if (error.response.status >= 500) {
        globalToast('Server error: An unexpected error occurred on our end.', 'error')
      } else if (error.response.status === 403) {
        globalToast('Access denied: You do not have permission.', 'warning')
      }

      return Promise.reject(error instanceof Error ? error : new Error(String(error)))
    }
  )

  return client
}

export const apiClient = createApiClient()
