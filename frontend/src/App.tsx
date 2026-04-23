import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense } from 'react'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { ProtectedRoute, PublicOnlyRoute } from './components/ui/ProtectedRoute'
import { ToastProvider } from './components/ui/Toast'
import { AppLayout } from './components/layout/AppLayout'
import { AdminLayout } from './components/layout/AdminLayout'
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
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
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

              {/* Chat Routes (protected) */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/chat" replace />} />
                <Route path="chat" element={<SuspensedPage><LazyChat /></SuspensedPage>} />
              </Route>

              {/* Admin Routes (protected) */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<SuspensedPage><LazyAdminDashboard /></SuspensedPage>} />
                <Route path="tenants" element={<SuspensedPage><LazyPlatformTenantManagement /></SuspensedPage>} />
                <Route path="documents" element={<SuspensedPage><LazyDocumentKnowledgeBase /></SuspensedPage>} />
                <Route path="users" element={<SuspensedPage><LazyUserManagement /></SuspensedPage>} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
