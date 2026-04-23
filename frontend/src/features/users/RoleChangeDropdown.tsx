import { useState } from 'react'
import { cn } from '../../utils/cn'
import type { UserRole } from '../../types/auth'

interface RoleChangeDropdownProps {
  userId: string
  currentRole: UserRole
  onConfirm: (userId: string, newRole: UserRole) => void
  isLoading?: boolean
}

const roleConfig: Record<UserRole, { color: string; bg: string; border: string; label: string }> = {
  admin: { color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'ADMIN' },
  analyst: { color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/30', label: 'ANALYST' },
  viewer: { color: 'text-slate-500', bg: 'bg-slate-500/10', border: 'border-slate-500/30', label: 'VIEWER' },
}

export function RoleChangeDropdown({ userId, currentRole, onConfirm, isLoading }: RoleChangeDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selected, setSelected] = useState<UserRole | null>(null)
  const config = roleConfig[currentRole]

  const handleConfirm = () => {
    if (selected && selected !== currentRole) {
      onConfirm(userId, selected)
      setSelected(null)
      setIsOpen(false)
    }
  }

  return (
    <div className="relative">
      {/* Current role badge */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-tighter transition-colors hover:opacity-80',
          config.color,
          config.bg,
          config.border,
        )}
        aria-label={`Change role for user. Current role: ${config.label}`}
        aria-expanded={isOpen}
        disabled={isLoading}
      >
        {config.label}
        <svg className="ml-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => { setIsOpen(false); setSelected(null) }} />
          <div className="absolute right-0 z-50 mt-1 w-48 rounded-sm border border-aasila-border bg-aasila-surface-ai p-2 shadow-lg">
            <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-aasila-muted">
              Change Role
            </p>
            {(Object.keys(roleConfig) as UserRole[]).map((role) => {
              const rc = roleConfig[role]
              const isSelected = selected === role
              return (
                <button
                  key={role}
                  type="button"
                  onClick={() => setSelected(role)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-xs transition-colors hover:bg-aasila-border/30',
                    isSelected ? 'bg-aasila-border/50 text-aasila-text' : 'text-aasila-muted',
                  )}
                >
                  <span
                    className={cn(
                      'inline-flex h-2 w-2 rounded-full',
                      rc.color.replace('text-', 'bg-'),
                    )}
                  />
                  <span className={cn('font-bold uppercase tracking-tighter', isSelected ? 'text-aasila-text' : 'text-aasila-muted')}>
                    {rc.label}
                  </span>
                  {role === currentRole && (
                    <span className="ml-auto text-[10px] text-aasila-muted">(current)</span>
                  )}
                </button>
              )
            })}
            {selected && selected !== currentRole && (
              <>
                <div className="my-2 border-t border-aasila-border" />
                <div className="flex gap-2 px-2">
                  <button
                    type="button"
                    onClick={() => { setIsOpen(false); setSelected(null) }}
                    className="flex-1 rounded-sm px-2 py-1 text-xs text-aasila-muted hover:bg-aasila-border/30"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    className="flex-1 rounded-sm bg-emerald-500 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-600"
                  >
                    Confirm
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
