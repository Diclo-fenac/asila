import axios, { type AxiosInstance } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

function getStoredTenantId(): string | null {
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

function getStoredAccessToken(): string | null {
  try {
    const auth = localStorage.getItem('aasila_auth')
    if (auth) {
      const parsed = JSON.parse(auth)
      return parsed?.access_token ?? null
    }
  } catch {
    return null
  }
  return null
}

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor: inject auth token and tenant ID
  client.interceptors.request.use((config) => {
    const token = getStoredAccessToken()
    const tenantId = getStoredTenantId()

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (tenantId) {
      config.headers['X-Tenant-Id'] = tenantId
    }

    return config
  })

  return client
}

export const apiClient = createApiClient()
