import { memo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'
import { cn } from '../utils/cn'
import { logout } from '../api/auth'

const recentConversations = [
  { id: '1', title: 'Classified Briefing Draft', active: true },
  { id: '2', title: 'Dataset Analysis: Trade', active: false },
  { id: '3', title: 'Q3 Policy Review', active: false },
]

export const Sidebar = memo(function Sidebar() {
  const user = useAuthStore((state) => state.user)
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <div className="flex h-full w-[260px] flex-shrink-0 flex-col border-r border-aasila-border bg-aasila-bg-sidebar">
      <div className="flex flex-col gap-4 p-4">
        {/* Logo */}
        <h1 className="text-base font-semibold leading-normal text-aasila-text">Aasila</h1>

        {/* New Chat Button */}
        <Link
          to="/chat"
          className="flex h-10 w-full cursor-pointer items-center justify-center overflow-hidden rounded-sm bg-aasila-surface-user px-4 text-sm font-medium leading-normal text-aasila-text transition-colors hover:bg-aasila-border"
        >
          + New Workspace
        </Link>

        {/* Recent Conversations */}
        <div className="mt-4 flex flex-col gap-1">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-aasila-muted">
            This Week
          </p>
          {recentConversations.map((conv) => (
            <Link
              key={conv.id}
              to="/chat"
              className={cn(
                'flex items-center gap-3 rounded-sm px-3 py-2 transition-colors cursor-pointer',
                conv.active
                  ? 'bg-aasila-border/50'
                  : 'hover:bg-aasila-border/30',
              )}
            >
              <svg
                className={cn(
                  'h-[18px] w-[18px]',
                  conv.active ? 'text-aasila-text' : 'text-aasila-muted',
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p
                className={cn(
                  'truncate text-sm font-medium leading-normal',
                  conv.active ? 'text-aasila-text' : 'text-aasila-muted',
                )}
              >
                {conv.title}
              </p>
            </Link>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-1">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-aasila-muted">
            Older
          </p>
          <div className="flex items-center gap-3 rounded-sm px-3 py-2 transition-colors hover:bg-aasila-border/30 cursor-pointer">
            <svg className="h-[18px] w-[18px] text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
            <p className="truncate text-sm font-medium leading-normal text-aasila-muted">Q3 Policy Review</p>
          </div>
        </div>
      </div>

      {/* User Profile */}
      <div className="relative mt-auto">
        <div 
          className="flex items-center gap-3 rounded-sm p-2 transition-colors hover:bg-aasila-border/30 cursor-pointer"
          onClick={() => setDropdownOpen(!dropdownOpen)}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-emerald-500/20">
            <span className="text-sm font-semibold text-emerald-500">
              {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
            </span>
          </div>
          <p className="truncate text-sm font-medium text-aasila-text">
            {user?.name || 'Unknown User'}
          </p>
          <svg className="ml-auto h-[18px] w-[18px] text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        
        {dropdownOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)}></div>
            <div className="absolute left-2 right-2 bottom-12 rounded-md border border-aasila-border bg-aasila-bg-main shadow-lg z-50 overflow-hidden glass-panel">
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
  )
})
