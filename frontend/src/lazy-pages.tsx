import { lazy } from 'react'


// Custom lazy loader that handles ChunkLoadErrors (e.g. when app updates during session)
function lazyImport(factory: () => Promise<any>) {
  return lazy(async () => {
    try {
      const module = await factory()
      if (module.default) return module
      return { default: Object.values(module)[0] }
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

// Lazy-loaded pages
export const LazyAdminDashboard = lazyImport(() => import('./pages/AdminDashboard'))
export const LazyPlatformTenantManagement = lazyImport(() => import('./pages/PlatformTenantManagement'))
export const LazyDocumentKnowledgeBase = lazyImport(() => import('./pages/DocumentKnowledgeBase'))
export const LazyUserManagement = lazyImport(() => import('./pages/UserManagement'))
export const LazyChat = lazyImport(() => import('./pages/Chat'))
export const LazyLoginPage = lazyImport(() => import('./pages/LoginPage'))
export const LazySignUpPage = lazyImport(() => import('./pages/SignUpPage'))
