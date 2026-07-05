import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, useState, useEffect } from 'react'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { ProtectedRoute, PublicOnlyRoute, AdminRoute } from './components/ui/ProtectedRoute'
import { ToastProvider } from './components/ui/Toast'
import { UnifiedShell } from './components/layout/UnifiedShell'
import {
  LazyAdminDashboard,
  LazyPlatformTenantManagement,
  LazyDocumentKnowledgeBase,
  LazyUserManagement,
  LazyChat,
  LazyLoginPage,
  LazySignUpPage,
} from './lazy-pages'

import { Skeleton } from './components/ui/Skeleton'

function LoadingFallback() {
  return (
    <div className="flex w-full flex-col gap-6 p-6">
      <Skeleton className="h-8 w-1/4" />
      <div className="grid gap-6 md:grid-cols-3">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

import { PageErrorBoundary } from './components/ui/PageErrorBoundary'

function SuspensedPage({ children }: { children: React.ReactNode }) {
  return (
    <PageErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
    </PageErrorBoundary>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (isOnline) return null

  return (
    <div className="fixed top-0 z-[100] w-full bg-error px-4 py-2 text-center text-sm font-medium text-error-container">
      You are currently offline. Please check your internet connection.
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <OfflineBanner />
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route
                path="/login"
                element={
                  <PublicOnlyRoute>
                    <SuspensedPage><LazyLoginPage /></SuspensedPage>
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="/signup"
                element={
                  <PublicOnlyRoute>
                    <SuspensedPage><LazySignUpPage /></SuspensedPage>
                  </PublicOnlyRoute>
                }
              />

              {/* Protected Unified Routes */}
              <Route
                element={
                  <ProtectedRoute>
                    <UnifiedShell />
                  </ProtectedRoute>
                }
              >
                {/* Chat Routes */}
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<SuspensedPage><LazyChat /></SuspensedPage>} />
                <Route path="/chat/:conversationId" element={<SuspensedPage><LazyChat /></SuspensedPage>} />

                {/* Admin Routes */}
                <Route path="/admin" element={
                  <AdminRoute>
                    <Outlet />
                  </AdminRoute>
                }>
                  <Route index element={<SuspensedPage><LazyAdminDashboard /></SuspensedPage>} />
                  <Route path="tenants" element={<SuspensedPage><LazyPlatformTenantManagement /></SuspensedPage>} />
                  <Route path="documents" element={<SuspensedPage><LazyDocumentKnowledgeBase /></SuspensedPage>} />
                  <Route path="users" element={<SuspensedPage><LazyUserManagement /></SuspensedPage>} />
                </Route>
              </Route>

              {/* Catch-all 404 */}
              <Route path="*" element={
                <div className="flex min-h-screen flex-col items-center justify-center bg-surface p-4 text-center">
                  <h1 className="font-heading text-6xl font-black text-primary">404</h1>
                  <h2 className="mt-4 text-xl font-bold text-on-surface">Page Not Found</h2>
                  <p className="mt-2 text-on-surface-variant">The page you are looking for doesn't exist or has been moved.</p>
                  <a href="/" className="mt-8 rounded-xl bg-on-surface text-surface-container-lowest px-6 py-2.5 text-sm font-bold tracking-wide transition-all hover:opacity-90 shadow-sm">
                    Return to Dashboard
                  </a>
                </div>
              } />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
