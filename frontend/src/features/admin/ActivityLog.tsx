import { cn } from '../../utils/cn'
import type { ActivityLogEntry } from '../../types/analytics'

interface ActivityLogProps {
  entries: ActivityLogEntry[]
  isLoading?: boolean
  onExportCsv?: () => void
}

// date-fns may not be installed, use a simple formatter
function formatTime(iso: string): string {
  try {
    const date = new Date(iso)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function ActivityLog({ entries, isLoading, onExportCsv }: ActivityLogProps) {
  if (isLoading) {
    return (
      <div className="col-span-12 overflow-hidden rounded-sm border border-aasila-border/50 bg-aasila-surface-ai lg:col-span-8">
        <div className="flex items-center justify-between border-b border-aasila-border/50 px-6 py-4">
          <div className="h-4 w-40 animate-pulse rounded bg-aasila-border" />
          <div className="h-3 w-20 animate-pulse rounded bg-aasila-border" />
        </div>
        <div className="space-y-0 divide-y divide-aasila-border/30">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-4 p-4">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-aasila-border" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-3/4 animate-pulse rounded bg-aasila-border" />
                <div className="h-3 w-1/2 animate-pulse rounded bg-aasila-border" />
              </div>
              <div className="h-3 w-12 animate-pulse rounded bg-aasila-border" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <div className="col-span-12 flex flex-col items-center justify-center rounded-sm border border-aasila-border/50 bg-aasila-surface-ai p-12 lg:col-span-8">
        <svg className="mb-3 h-8 w-8 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p className="text-sm font-medium text-aasila-text">No activity yet</p>
        <p className="text-xs text-aasila-muted">Actions will appear here as they happen.</p>
      </div>
    )
  }

  return (
    <div className="col-span-12 flex flex-col overflow-hidden rounded-sm border border-aasila-border/50 bg-aasila-surface-ai lg:col-span-8">
      <div className="flex items-center justify-between border-b border-aasila-border/50 px-6 py-4">
        <h3 className="text-sm font-bold uppercase tracking-widest font-mono text-aasila-text">
          Recent Activity Log
        </h3>
        {onExportCsv && (
          <button
            type="button"
            onClick={onExportCsv}
            className="text-[10px] font-mono text-emerald-500 hover:underline"
          >
            EXPORT_CSV
          </button>
        )}
      </div>

      <div className="divide-y divide-aasila-border/30">
        {entries.slice(0, 10).map((entry) => (
          <div
            key={entry.id}
            className="flex items-center gap-4 p-4 transition-colors hover:bg-aasila-bg-main"
          >
            <div
              className={cn(
                'h-1.5 w-1.5 shrink-0 rounded-full',
                entry.severity === 'error' && 'bg-red-500',
                entry.severity === 'warning' && 'bg-amber-500',
                entry.severity === 'info' && 'bg-emerald-500',
              )}
            />
            <div className="flex-1 text-[13px]">
              <span className="font-bold text-aasila-text">{entry.user}</span>
              <span className="px-1 text-aasila-muted">{entry.action}</span>
              {entry.target && (
                <span className="rounded-sm border border-aasila-border/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[12px] text-emerald-500">
                  {entry.target}
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono text-aasila-muted">
              {formatTime(entry.timestamp)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
