import { lazy, Suspense } from 'react'
import { LoadingSpinner } from './components/ui/LoadingSpinner'

function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <LoadingSpinner className="h-8 w-8" />
    </div>
  )
}

// Lazy-loaded pages
export const LazyAdminDashboard = lazy(() => import('./pages/AdminDashboard').then(m => ({ default: m.AdminDashboard })))
export const LazyPlatformTenantManagement = lazy(() => import('./pages/PlatformTenantManagement').then(m => ({ default: m.PlatformTenantManagement })))
export const LazyDocumentKnowledgeBase = lazy(() => import('./pages/DocumentKnowledgeBase').then(m => ({ default: m.DocumentKnowledgeBase })))
export const LazyUserManagement = lazy(() => import('./pages/UserManagement').then(m => ({ default: m.UserManagement })))
export const LazyChat = lazy(() => import('./pages/Chat').then(m => ({ default: m.Chat })))
export const LazyLoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })))
export const LazySignUpPage = lazy(() => import('./pages/SignUpPage').then(m => ({ default: m.SignUpPage })))

// Wrap a lazy component with Suspense
export function withSuspense<T extends Record<string, unknown>>(Component: React.ComponentType<T>, fallback?: React.ReactNode) {
  return function SuspendedComponent(props: T) {
    return (
      <Suspense fallback={fallback ?? <PageLoader />}>
        <Component {...props} />
      </Suspense>
    )
  }
}
