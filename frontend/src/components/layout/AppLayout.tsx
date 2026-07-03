import { useState, useEffect } from 'react'
import { Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'
import { MobileSidebar } from '../ui/MobileSidebar'
import { cn } from '../../utils/cn'

export function AppLayout() {
  const user = useAuthStore((state) => state.user)
  const [sidebarOpen, setSidebarOpen] = useState(false) // Desktop & Mobile toggle

  // Auto-hide on resize if needed
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = () => {
      // we can leave it as is or auto-open
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-aasila-bg-main font-display text-aasila-text relative">
      {/* Floating Sidebar (Desktop & Mobile combined logic or keep separate) */}
      
      {/* Mobile Drawer */}
      <MobileSidebar isOpen={sidebarOpen && window.innerWidth < 1024} onClose={() => setSidebarOpen(false)}>
        <MobileSidebarContent user={user} />
      </MobileSidebar>

      {/* Desktop Floating Sidebar */}
      <div 
        className={cn(
          "fixed left-4 top-4 bottom-4 w-64 rounded-xl border border-aasila-border glass-panel-floating z-50 transition-transform duration-300 hidden lg:flex flex-col",
          sidebarOpen ? "translate-x-0" : "-translate-x-[120%]"
        )}
      >
        <DesktopSidebar user={user} onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main Container */}
      <div className="flex flex-1 flex-col overflow-hidden w-full relative">
        {/* Top Header (Glassmorphic) */}
        <header className="absolute top-0 left-0 right-0 z-40 flex h-14 items-center gap-3 border-b border-aasila-border glass-panel px-4">
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
          <h1 className="text-sm font-semibold tracking-wide">Aasila Workspace</h1>
        </header>

        <main className="relative flex-1 overflow-hidden pt-14">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function DesktopSidebar({ user, onClose }: { user: { name: string } | null, onClose: () => void }) {
  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex items-center justify-between p-4 pb-2">
        <h1 className="text-base font-semibold text-aasila-text tracking-wide">Aasila</h1>
        <button onClick={onClose} className="p-1 rounded-md text-aasila-muted hover:bg-aasila-surface-user">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="flex flex-col gap-4 p-4 pt-2">
        <Link
          to="/chat"
          className="flex h-10 w-full items-center justify-center rounded-md bg-[#1E201F] text-[#FAF7F5] dark:bg-[#FAF7F5] dark:text-[#1E201F] px-4 text-sm font-medium transition-all hover:opacity-90 shadow-sm"
        >
          + New Workspace
        </Link>
        <div className="mt-4 flex flex-col gap-1">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-aasila-muted">This Week</p>
          <Link to="/chat" className="flex items-center gap-3 rounded-md bg-aasila-surface-user px-3 py-2 border border-transparent hover:border-brand-accent/30 transition-colors">
            <svg className="h-[18px] w-[18px] text-brand-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="truncate text-sm font-medium text-aasila-text">Classified Briefing Draft</p>
          </Link>
        </div>
      </div>
      <div className="mt-auto flex items-center gap-3 p-4 border-t border-aasila-border/50 bg-aasila-surface/50">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-accent/20">
          <span className="text-sm font-bold text-brand-accent">
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
    <div className="flex flex-col gap-4 p-4 h-full">
      <Link
        to="/chat"
        onClick={() => {}}
        className="flex h-10 w-full items-center justify-center rounded-md bg-[#1E201F] text-[#FAF7F5] dark:bg-[#FAF7F5] dark:text-[#1E201F] px-4 text-sm font-medium transition-all hover:opacity-90 shadow-sm"
      >
        + New Workspace
      </Link>
      <Link to="/chat" className="flex items-center gap-3 rounded-md px-3 py-2 bg-aasila-surface-user border border-transparent hover:border-brand-accent/30">
        <svg className="h-[18px] w-[18px] text-brand-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="truncate text-sm font-medium text-aasila-text">Classified Briefing Draft</p>
      </Link>
      <div className="mt-auto flex items-center gap-3 p-2 pt-4 border-t border-aasila-border/50">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-accent/20">
          <span className="text-sm font-bold text-brand-accent">
            {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
          </span>
        </div>
        <p className="truncate text-sm font-medium text-aasila-text">{user?.name || 'Unknown User'}</p>
      </div>
    </div>
  )
}
