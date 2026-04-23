import { useState, useEffect } from 'react'
import { Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'
import { MobileSidebar } from '../ui/MobileSidebar'

export function AppLayout() {
  const user = useAuthStore((state) => state.user)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Close on resize (switched to desktop)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    mq.addEventListener('change', (e) => { if (e.matches) setMobileOpen(false) })
    return () => mq.removeEventListener('change', () => {})
  }, [])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-aasila-bg-main font-display text-aasila-text">
      {/* Desktop sidebar */}
      <div className="hidden border-r border-aasila-border bg-aasila-bg-sidebar lg:flex lg:w-[260px] lg:flex-shrink-0">
        <DesktopSidebar user={user} />
      </div>

      {/* Mobile drawer */}
      <MobileSidebar isOpen={mobileOpen} onClose={() => setMobileOpen(false)}>
        <MobileSidebarContent user={user} />
      </MobileSidebar>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="flex h-12 items-center gap-3 border-b border-aasila-border bg-aasila-bg-main px-4 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-sm p-1 text-aasila-muted transition-colors hover:text-aasila-text"
            aria-label="Open navigation"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-sm font-semibold">Aasila</h1>
        </header>

        <main className="relative flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function DesktopSidebar({ user }: { user: { name: string } | null }) {
  return (
    <div className="flex h-full w-[260px] flex-col border-r border-aasila-border bg-aasila-bg-sidebar">
      <div className="flex flex-col gap-4 p-4">
        <h1 className="text-base font-semibold text-aasila-text">Aasila</h1>
        <Link
          to="/chat"
          className="flex h-10 w-full items-center justify-center rounded-sm bg-aasila-surface-user px-4 text-sm font-medium text-aasila-text transition-colors hover:bg-aasila-border"
        >
          + New Workspace
        </Link>
        <div className="mt-4 flex flex-col gap-1">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-aasila-muted">This Week</p>
          <Link to="/chat" className="flex items-center gap-3 rounded-sm bg-aasila-border/50 px-3 py-2">
            <svg className="h-[18px] w-[18px] text-aasila-text" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="truncate text-sm font-medium text-aasila-text">Classified Briefing Draft</p>
          </Link>
        </div>
      </div>
      <div className="mt-auto flex items-center gap-3 rounded-sm p-2 hover:bg-aasila-border/30">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-emerald-500/20">
          <span className="text-sm font-semibold text-emerald-500">
            {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
          </span>
        </div>
        <p className="truncate text-sm font-medium text-aasila-text">{user?.name || 'Unknown User'}</p>
      </div>
    </div>
  )
}

function MobileSidebarContent({ user }: { user: { name: string } | null }) {
  return (
    <div className="flex flex-col gap-4 p-4">
      <Link
        to="/chat"
        onClick={() => {}}
        className="flex h-10 w-full items-center justify-center rounded-sm bg-aasila-surface-user px-4 text-sm font-medium text-aasila-text transition-colors hover:bg-aasila-border"
      >
        + New Workspace
      </Link>
      <Link to="/chat" className="flex items-center gap-3 rounded-sm px-3 py-2 hover:bg-aasila-border/30">
        <svg className="h-[18px] w-[18px] text-aaseline-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="truncate text-sm text-aaseline-muted">Classified Briefing Draft</p>
      </Link>
      <div className="mt-auto flex items-center gap-3 p-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-emerald-500/20">
          <span className="text-sm font-semibold text-emerald-500">
            {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
          </span>
        </div>
        <p className="truncate text-sm font-medium text-aasila-text">{user?.name || 'Unknown User'}</p>
      </div>
    </div>
  )
}
