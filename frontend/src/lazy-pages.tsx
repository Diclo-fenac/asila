import { lazy, Suspense } from 'react'
import React from 'react'
import { LoadingSpinner } from './components/ui/LoadingSpinner'

// Custom lazy loader that handles ChunkLoadErrors (e.g. when app updates during session)
function lazyImport(factory: () => Promise<any>) {
  return lazy(async () => {
    try {
      const component = await factory()
      return component
    } catch (error) {
      const isChunkLoadError = error instanceof Error && 
        (error.message.includes('Failed to fetch dynamically imported module') ||
         error.message.includes('Importing a module script failed'));
      
      if (isChunkLoadError) {
        // Automatically reload the page to get the latest chunks
        window.location.reload()
      }
      throw error
    }
  })
}

function PageLoader() {
  return (
    <div className="flex h-[80vh] items-center justify-center">
      <LoadingSpinner className="h-8 w-8" />
    </div>
  )
}

// Lazy-loaded pages
export const LazyAdminDashboard = lazyImport(() => import('./pages/AdminDashboard'))
export const LazyPlatformTenantManagement = lazyImport(() => import('./pages/PlatformTenantManagement'))
export const LazyDocumentKnowledgeBase = lazyImport(() => import('./pages/DocumentKnowledgeBase'))
export const LazyUserManagement = lazyImport(() => import('./pages/UserManagement'))
export const LazyChat = lazyImport(() => import('./pages/Chat'))
export const LazyLoginPage = lazyImport(() => import('./pages/LoginPage'))
export const LazySignUpPage = lazyImport(() => import('./pages/SignUpPage'))

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
