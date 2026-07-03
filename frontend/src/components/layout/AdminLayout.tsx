import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'
import { useThemeStore } from '../../store/useThemeStore'
import { cn } from '../../utils/cn'
import { MobileSidebar } from '../ui/MobileSidebar'

const navItems = [
  { path: '/admin', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { path: '/admin/tenants', label: 'Tenants', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { path: '/admin/documents', label: 'Documents', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { path: '/admin/users', label: 'User Roles', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
]

export function AdminLayout() {
  const user = useAuthStore((state) => state.user)
  const tenant = useAuthStore((state) => state.tenant)
  const dark = useThemeStore((state) => state.dark)
  const toggleTheme = useThemeStore((state) => state.toggle)
  const location = useLocation()
  
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = (e: MediaQueryListEvent) => { if (e.matches) setSidebarOpen(false) }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const isActive = (path: string) => {
    if (path === '/admin') return location.pathname === '/admin'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="flex min-h-screen bg-aasila-bg-main font-display text-aasila-text selection:bg-brand-accent/20 relative">
      
      {/* Mobile drawer */}
      <MobileSidebar isOpen={sidebarOpen && window.innerWidth < 1024} onClose={() => setSidebarOpen(false)}>
        <AdminSidebarContent user={user} tenant={tenant} isActive={isActive} onClose={() => setSidebarOpen(false)} />
      </MobileSidebar>

      {/* Desktop Floating Sidebar */}
      <aside 
        className={cn(
          "fixed left-4 top-4 bottom-4 w-64 rounded-xl border border-aasila-border glass-panel-floating z-50 transition-transform duration-300 hidden lg:flex flex-col",
          sidebarOpen ? "translate-x-0" : "-translate-x-[120%]"
        )}
      >
        <AdminSidebarContent user={user} tenant={tenant} isActive={isActive} onClose={() => setSidebarOpen(false)} />
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden w-full relative">
        {/* Top bar (Glassmorphic) */}
        <header className="absolute top-0 left-0 right-0 z-40 flex h-16 items-center justify-between border-b border-aasila-border glass-panel px-4 lg:px-8">
          <div className="flex items-center gap-4 lg:gap-6">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-md p-1.5 text-aasila-muted transition-colors hover:text-aasila-text hover:bg-aasila-surface-user"
              aria-label="Toggle navigation"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <span className="font-mono text-lg font-black tracking-tighter text-brand-accent">AASILA</span>
          </div>

          <div className="flex items-center gap-5">
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-md p-1.5 text-aasila-muted transition-colors hover:text-aasila-text hover:bg-aasila-surface-user"
              aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {dark ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>
            <div
              className="flex h-8 w-8 items-center justify-center rounded-md border border-aasila-border bg-brand-accent/10 text-sm font-bold text-brand-accent"
              title={user?.name}
            >
              {user?.name[0] || 'U'}
            </div>
          </div>
        </header>

        {/* Main */}
        <main className="min-h-screen pt-16 flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function AdminSidebarContent({ user, tenant, isActive, onClose }: any) {
  return (
    <>
      <div className="flex items-center justify-between px-6 pt-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-brand-accent/20 bg-brand-accent/10 shadow-sm">
            <span className="text-sm font-bold text-brand-accent">{user?.name[0] || 'A'}</span>
          </div>
          <div className="flex w-32 flex-col">
            <span className="truncate text-sm font-bold font-mono text-aasila-text">
              {tenant?.name || 'Aasila'} Tenant
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-brand-accent">Admin Console</span>
          </div>
        </div>
        <button onClick={onClose} className="p-1 rounded-md text-aasila-muted hover:bg-aasila-surface-user lg:hidden">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3" aria-label="Admin navigation">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 transition-all duration-150',
              isActive(item.path)
                ? 'bg-brand-accent/10 font-semibold text-brand-accent shadow-sm border border-brand-accent/20'
                : 'text-aasila-muted hover:bg-aasila-surface-user hover:text-aasila-text border border-transparent',
            )}
            aria-current={isActive(item.path) ? 'page' : undefined}
          >
            <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            <span className="text-[14px] tracking-tight">{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="mt-auto space-y-4 px-3 pb-6">
        <button
          type="button"
          className="w-full rounded-md bg-[#1E201F] text-[#FAF7F5] dark:bg-[#FAF7F5] dark:text-[#1E201F] py-2.5 text-xs font-bold uppercase tracking-wider transition-opacity hover:opacity-90 shadow-sm"
        >
          New System Report
        </button>
      </div>
    </>
  )
}
