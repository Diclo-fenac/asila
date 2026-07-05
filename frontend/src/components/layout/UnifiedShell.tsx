import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'
import { MobileSidebar } from '../ui/MobileSidebar'
import { cn } from '../../utils/cn'
import { useConversations } from '../../hooks/useConversations'
import { logout } from '../../api/auth'

const adminNavItems = [
  { path: '/admin', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { path: '/admin/tenants', label: 'Tenants', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { path: '/admin/documents', label: 'Documents', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { path: '/admin/users', label: 'User Roles', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
]

export function UnifiedShell() {
  const user = useAuthStore((state) => state.user)
  const tenant = useAuthStore((state) => state.tenant)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  
  const isAdmin = location.pathname.startsWith('/admin')

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = (e: MediaQueryListEvent) => { if (e.matches) setSidebarOpen(false) }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-aasila-bg-main font-display text-aasila-text relative selection:bg-brand-accent/20">
      
      {/* Mobile drawer */}
      <MobileSidebar isOpen={sidebarOpen && window.innerWidth < 1024} onClose={() => setSidebarOpen(false)}>
        <SidebarContent user={user} tenant={tenant} isAdmin={isAdmin} onClose={() => setSidebarOpen(false)} />
      </MobileSidebar>

      {/* Desktop Permanent Sidebar */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-aasila-border bg-aasila-bg-main z-10 shrink-0">
        <SidebarContent user={user} tenant={tenant} isAdmin={isAdmin} onClose={() => {}} />
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden w-full relative">
        {/* Top bar */}
        <header className="absolute top-0 left-0 right-0 z-40 flex h-16 items-center justify-between border-b border-aasila-border glass-panel px-4 lg:px-8">
          <div className="flex items-center gap-4 lg:gap-6">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-md p-1.5 text-aasila-muted transition-colors hover:text-aasila-text hover:bg-aasila-surface-user lg:hidden"
              aria-label="Toggle navigation"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <span className="font-mono text-lg font-black tracking-tighter text-brand-accent">AASILA</span>
            {isAdmin && <span className="hidden lg:inline-block ml-2 text-xs font-mono font-semibold text-brand-accent px-2 py-0.5 rounded-full bg-brand-accent/10 border border-brand-accent/20 tracking-wider">ADMIN CONSOLE</span>}
          </div>

          <div className="flex items-center gap-5">
            {/* Removed top-right user dropdown, moved to sidebar */}
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

function SidebarContent({ user, tenant, isAdmin, onClose }: any) {
  const location = useLocation()
  const navigate = useNavigate()
  const { conversationId } = useParams()
  const { conversations, createConversation, deleteConversation, renameConversation } = useConversations()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const isActive = (path: string) => {
    if (path === '/admin') return location.pathname === '/admin'
    return location.pathname.startsWith(path)
  }
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <>
      <div className="flex items-center justify-between px-4 lg:px-6 pt-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-brand-accent/20 bg-brand-accent/10 shadow-sm shrink-0">
            <span className="text-sm font-bold text-brand-accent">{user?.name?.[0] || 'U'}</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="truncate text-sm font-bold font-mono text-aasila-text">
              {tenant?.name || 'Aasila'} Tenant
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-brand-accent truncate">
              {isAdmin ? 'Admin Console' : 'Workspace'}
            </span>
          </div>
        </div>
        <button onClick={onClose} className="p-1 rounded-md text-aasila-muted hover:bg-aasila-surface-user lg:hidden shrink-0" aria-label="Close Sidebar">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3 overflow-y-auto" aria-label="Main navigation">
        {isAdmin ? (
          <>
            {adminNavItems.map((item) => (
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
            <div className="mt-8 px-3 text-xs font-semibold uppercase tracking-wider text-aasila-muted mb-2">Switch Context</div>
            <Link
              to="/chat"
              onClick={onClose}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-aasila-muted hover:bg-aasila-surface-user hover:text-aasila-text border border-transparent transition-all"
            >
              <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span className="text-[14px] tracking-tight">Return to Chat</span>
            </Link>
          </>
        ) : (
          <>
            <button
              onClick={async () => {
                const newConv = await createConversation()
                navigate(`/chat/${newConv.id}`)
                onClose()
              }}
              className="flex w-full items-center justify-center rounded-md bg-aasila-text text-aasila-bg-main px-4 py-2 text-sm font-bold tracking-wide transition-all hover:opacity-90 shadow-sm mb-6"
            >
              + New Workspace
            </button>
            
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-aasila-muted mb-2">Recent</p>
            {conversations.length === 0 && (
              <p className="px-3 text-xs text-aasila-muted italic">No conversations yet.</p>
            )}
            {conversations.map((conv) => (
              <div key={conv.id} className="group flex items-center gap-1">
                {editingId === conv.id ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={async () => {
                      if (editTitle.trim() && editTitle !== conv.title) {
                        await renameConversation({ id: conv.id, title: editTitle })
                      }
                      setEditingId(null)
                    }}
                    onKeyDown={async (e) => {
                      if (e.key === 'Enter') {
                        if (editTitle.trim() && editTitle !== conv.title) {
                          await renameConversation({ id: conv.id, title: editTitle })
                        }
                        setEditingId(null)
                      }
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    className="flex-1 rounded-md bg-aasila-surface-user px-3 py-1.5 text-sm text-aasila-text outline-none focus:ring-1 focus:ring-brand-accent"
                    autoFocus
                  />
                ) : (
                  <Link 
                    to={`/chat/${conv.id}`} 
                    onClick={onClose}
                    className={cn(
                      "flex flex-1 min-w-0 items-center gap-3 rounded-md px-3 py-2 border transition-colors overflow-hidden",
                      conversationId === conv.id 
                        ? "bg-aasila-surface-user border-brand-accent/30 text-brand-accent" 
                        : "border-transparent hover:border-brand-accent/30 text-aasila-text"
                    )}
                  >
                    <svg className="h-[18px] w-[18px] shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="truncate text-sm font-medium">{conv.title}</p>
                  </Link>
                )}
                <div className="flex shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => {
                      setEditTitle(conv.title)
                      setEditingId(conv.id)
                    }}
                    className="p-1.5 text-aasila-muted hover:text-aasila-text rounded hover:bg-aasila-surface-user"
                    title="Rename"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button
                    onClick={async () => {
                      if (confirm('Delete this conversation?')) {
                        await deleteConversation(conv.id)
                        if (conversationId === conv.id) navigate('/chat')
                      }
                    }}
                    className="p-1.5 text-aasila-muted hover:text-red-400 rounded hover:bg-aasila-surface-user"
                    title="Delete"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
            
            {user?.role?.toUpperCase() === 'ADMIN' && (
              <>
                <div className="mt-8 px-3 text-xs font-semibold uppercase tracking-wider text-aasila-muted mb-2">Switch Context</div>
                <Link
                  to="/admin"
                  onClick={onClose}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-aasila-muted hover:bg-aasila-surface-user hover:text-aasila-text border border-transparent transition-all"
                >
                  <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-[14px] tracking-tight">Admin Console</span>
                </Link>
              </>
            )}
          </>
        )}
      </nav>

      {/* Footer User Profile */}
      <div className="mt-auto border-t border-aasila-border/50 bg-aasila-surface/30">
        <div className="relative p-3">
          <div 
            className="flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-aasila-border/30 cursor-pointer"
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-accent/20 border border-brand-accent/30">
              <span className="text-sm font-semibold text-brand-accent">
                {user?.name?.[0]?.toUpperCase() || 'U'}
              </span>
            </div>
            <div className="flex flex-col min-w-0">
              <p className="truncate text-sm font-bold text-aasila-text">{user?.name || 'Unknown User'}</p>
              <p className="truncate text-[10px] text-aasila-muted uppercase tracking-wider">{user?.role || 'user'}</p>
            </div>
            <svg className="ml-auto h-4 w-4 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </div>
          
          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)}></div>
              <div className="absolute left-2 right-2 bottom-16 rounded-md border border-aasila-border bg-aasila-bg-main shadow-lg z-50 overflow-hidden glass-panel">
                <div className="px-3 py-2 border-b border-aasila-border/50">
                  <p className="text-xs font-bold text-aasila-text truncate">{user?.name}</p>
                  <p className="text-[10px] text-aasila-muted truncate font-mono mt-0.5">{user?.email}</p>
                </div>
                <div className="p-1">
                  <button
                    onClick={async () => {
                      setDropdownOpen(false)
                      await logout()
                    }}
                    className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-red-400 hover:bg-red-500/10 rounded-sm transition-colors text-left font-medium"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Sign Out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
