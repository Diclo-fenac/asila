import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense } from 'react'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { ProtectedRoute, PublicOnlyRoute } from './components/ui/ProtectedRoute'
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

function LoadingFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
    </div>
  )
}

function SuspensedPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
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

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
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
                <Route path="/admin">
                  <Route index element={<SuspensedPage><LazyAdminDashboard /></SuspensedPage>} />
                  <Route path="tenants" element={<SuspensedPage><LazyPlatformTenantManagement /></SuspensedPage>} />
                  <Route path="documents" element={<SuspensedPage><LazyDocumentKnowledgeBase /></SuspensedPage>} />
                  <Route path="users" element={<SuspensedPage><LazyUserManagement /></SuspensedPage>} />
                </Route>
              </Route>

              {/* Catch-all 404 */}
              <Route path="*" element={
                <div className="flex min-h-screen flex-col items-center justify-center bg-aasila-bg-main p-4 text-center">
                  <h1 className="text-6xl font-black text-brand-accent">404</h1>
                  <h2 className="mt-4 text-xl font-bold text-aasila-text">Page Not Found</h2>
                  <p className="mt-2 text-aasila-muted">The page you are looking for doesn't exist or has been moved.</p>
                  <a href="/" className="mt-8 rounded-md bg-aasila-text text-aasila-bg-main px-6 py-2.5 text-sm font-bold tracking-wide transition-all hover:opacity-90 shadow-sm">
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
