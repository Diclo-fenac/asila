import { cn } from '../../utils/cn'
import type { Tenant } from '../../types/tenant'

interface TenantCardProps {
  tenant: Tenant
  onManage?: (id: string) => void
  onCancel?: (id: string) => void
}

const statusConfig: Record<string, { label: string; color: string; bg: string; border: string; pulse: boolean }> = {
  active: { label: 'Active', color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', pulse: false },
  provisioning: { label: 'Provisioning', color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/30', pulse: true },
  offline: { label: 'Offline', color: 'text-slate-500', bg: 'bg-slate-500/10', border: 'border-slate-500/30', pulse: false },
  suspended: { label: 'Suspended', color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30', pulse: false },
}

export function TenantCard({ tenant, onManage, onCancel }: TenantCardProps) {
  const status = statusConfig[tenant.status] ?? statusConfig.offline

  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-sm border border-aasila-border bg-aasila-surface-ai p-5',
        tenant.status === 'offline' && 'opacity-70',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-aasila-text">{tenant.name}</h3>
          <span className="font-mono text-[12px] text-aasila-muted">{tenant.id.slice(0, 8).toUpperCase()}</span>
        </div>
        <span
          className={cn(
            'flex items-center gap-1 rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider',
            status.color,
            status.bg,
            status.border,
          )}
        >
          {status.pulse && <span className="h-1 w-1 animate-pulse rounded-full bg-current" />}
          {status.label}
        </span>
      </div>

      {/* Activity bar */}
      {tenant.status === 'active' && tenant.health_index !== undefined && (
        <div className="flex h-8 items-end gap-1">
          {Array.from({ length: 8 }).map((_, i) => {
            const ratio = tenant.health_index! / 100
            const height = Math.max(15, Math.random() * 60 + 20 * ratio)
            return (
              <div
                key={i}
                className="w-1 rounded-[1px] bg-emerald-500"
                style={{ height: `${height}%` }}
              />
            )
          })}
        </div>
      )}

      {/* Provisioning progress */}
      {tenant.status === 'provisioning' && (
        <div className="flex flex-1 items-center justify-center py-2">
          <div className="flex w-full flex-col items-center gap-2">
            <div className="h-1 w-full max-w-[120px] overflow-hidden rounded-full bg-aasila-bg-main">
              <div className="h-full animate-pulse rounded-full bg-amber-400" style={{ width: '66%' }} />
            </div>
            <span className="text-[10px] font-mono text-aasila-muted">Creating DB Schema...</span>
          </div>
        </div>
      )}

      {/* Offline flatline */}
      {tenant.status === 'offline' && (
        <div className="flex h-8 items-end gap-1">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="w-1 rounded-[1px] bg-slate-300" style={{ height: '16%' }} />
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-2 flex items-center justify-between border-t border-aasila-border/50 pt-4">
        <span className="text-[11px] font-medium uppercase text-aasila-muted">
          {tenant.last_sync ? `Last Sync: ${tenant.last_sync}` : tenant.status === 'provisioning' ? 'Est: 45s remaining' : 'Maintenance Schedule: 22:00'}
        </span>
        <div className="flex items-center gap-2">
          {tenant.status === 'provisioning' && onCancel && (
            <button
              type="button"
              onClick={() => onCancel(tenant.id)}
              className="text-aasila-muted transition-colors hover:text-red-500"
              aria-label={`Cancel provisioning for ${tenant.name}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          {onManage && (
            <button
              type="button"
              onClick={() => onManage(tenant.id)}
              className="text-aasila-muted transition-colors hover:text-aasila-text"
              aria-label={`Manage ${tenant.name}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
