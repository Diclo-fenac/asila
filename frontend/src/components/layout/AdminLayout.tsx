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
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    mq.addEventListener('change', (e) => { if (e.matches) setMobileOpen(false) })
    return () => mq.removeEventListener('change', () => {})
  }, [])

  const isActive = (path: string) => {
    if (path === '/admin') return location.pathname === '/admin'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="flex min-h-screen bg-aasila-bg-main font-display text-aasila-text selection:bg-emerald-500/20">
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 z-50 hidden h-screen w-64 flex-col border-r border-aasila-border bg-aasila-bg-sidebar py-6 lg:flex">
        <div className="mb-8 px-6">
          <div className="mb-1 flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-sm border border-aasila-border bg-emerald-500/20">
              <span className="text-sm font-bold text-emerald-500">{user?.name[0] || 'A'}</span>
            </div>
            <div className="flex w-32 flex-col">
              <span className="truncate text-sm font-bold font-mono text-aasila-text">
                {tenant?.name || 'Aasila'} Tenant
              </span>
              <span className="font-mono text-[10px] uppercase tracking-widest text-aasila-muted">Admin Console</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3" aria-label="Admin navigation">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-sm px-3 py-2 transition-colors duration-150',
                isActive(item.path)
                  ? 'border-r-2 border-emerald-500 bg-aasila-border/50 font-semibold text-emerald-500'
                  : 'text-aasila-muted hover:bg-aasila-border/30 hover:text-aasila-text',
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

        <div className="mt-auto space-y-4 px-3">
          <button
            type="button"
            className="w-full rounded-sm bg-background-dark py-2.5 text-xs font-bold uppercase tracking-wider text-emerald-500 transition-opacity hover:opacity-90"
          >
            New System Report
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      <MobileSidebar isOpen={mobileOpen} onClose={() => setMobileOpen(false)}>
        <nav className="flex-1 space-y-1 px-3" aria-label="Admin navigation">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={cn(
                'flex items-center gap-3 rounded-sm px-3 py-2 transition-colors duration-150',
                isActive(item.path)
                  ? 'border-r-2 border-emerald-500 bg-aasila-border/50 font-semibold text-emerald-500'
                  : 'text-aasila-muted hover:bg-aasila-border/30 hover:text-aasila-text',
              )}
            >
              <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              <span className="text-[14px] tracking-tight">{item.label}</span>
            </Link>
          ))}
        </nav>
      </MobileSidebar>

      {/* Top bar */}
      <header className="fixed right-0 top-0 z-40 flex h-16 w-full items-center justify-between border-b border-aasila-border bg-aasila-bg-main/90 px-4 backdrop-blur-md lg:left-64 lg:w-[calc(100%-16rem)] lg:px-8">
        <div className="flex items-center gap-4 lg:gap-6">
          {/* Hamburger for mobile */}
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-sm p-1 text-aasila-muted transition-colors hover:text-aasila-text lg:hidden"
            aria-label="Open navigation"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="font-mono text-lg font-black tracking-tighter text-emerald-500">AASILA</span>
        </div>

        <div className="flex items-center gap-5">
          <button
            type="button"
            onClick={toggleTheme}
            className="rounded-sm p-1 text-aasila-muted transition-colors hover:text-aasila-text"
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
            className="flex h-8 w-8 items-center justify-center rounded-sm border border-aasila-border bg-emerald-500/10 text-sm font-bold text-emerald-500"
            title={user?.name}
          >
            {user?.name[0] || 'U'}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="min-h-screen pt-16 lg:ml-64">
        <Outlet />
      </main>
    </div>
  )
}
