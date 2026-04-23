import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'

interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const navigate = useNavigate()

  if (!isAuthenticated) {
    // Redirect to login, preserving intended destination
    const currentPath = window.location.pathname + window.location.search
    navigate(`/login?redirect=${encodeURIComponent(currentPath)}`, { replace: true })

    return fallback ?? (
      <div className="flex min-h-screen items-center justify-center bg-aasila-bg-main">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <p className="mt-4 text-sm text-aasila-muted">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

// For routes that should only be accessible when NOT authenticated (login/signup)
export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const navigate = useNavigate()

  if (isAuthenticated) {
    navigate('/chat', { replace: true })
    return null
  }

  return <>{children}</>
}
