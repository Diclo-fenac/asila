import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'

interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    const currentPath = location.pathname + location.search
    return (
      <>
        {fallback ?? (
          <div className="flex min-h-screen items-center justify-center bg-aasila-bg-main">
            <div className="text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
              <p className="mt-4 text-sm text-aasila-muted">Redirecting to login...</p>
            </div>
          </div>
        )}
        <Navigate to={`/login?redirect=${encodeURIComponent(currentPath)}`} replace />
      </>
    )
  }

  return <>{children}</>
}

// For routes that should only be accessible when NOT authenticated (login/signup)
export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (isAuthenticated) {
    return <Navigate to="/chat" replace />
  }

  return <>{children}</>
}
