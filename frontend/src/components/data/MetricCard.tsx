import { memo } from 'react'
import { cn } from '../../utils/cn'
import { Sparkline } from './Sparkline'
import { LoadingSpinner } from '../ui/LoadingSpinner'

interface MetricCardProps {
  label: string
  value: string | number
  deltaPercent?: number
  history?: number[]
  icon?: React.ReactNode
  isLoading?: boolean
  className?: string
  variant?: 'default' | 'dark'
}

export const MetricCard = memo(function MetricCard({
  label,
  value,
  deltaPercent,
  history,
  icon,
  isLoading,
  className,
  variant = 'default',
}: MetricCardProps) {
  const isDark = variant === 'dark'

  if (isLoading) {
    return (
      <div
        className={cn(
          'flex flex-col justify-between rounded-sm border p-6',
          isDark
            ? 'border-emerald-500/20 bg-gray-900 text-emerald-400'
            : 'border-aasila-border/50 bg-aasila-surface-ai',
          className,
        )}
      >
        <div className="space-y-3">
          <div className="flex items-start justify-between">
            <div className={cn('h-3 w-24 animate-pulse rounded', isDark ? 'bg-emerald-500/20' : 'bg-aasila-border')} />
            {icon && <div className="h-4 w-4 animate-pulse rounded bg-aasila-border" />}
          </div>
          <div className={cn('h-8 w-20 animate-pulse rounded', isDark ? 'bg-emerald-500/20' : 'bg-aasila-border')} />
          {deltaPercent !== undefined && (
            <div className={cn('h-2 w-32 animate-pulse rounded', isDark ? 'bg-emerald-500/20' : 'bg-aasila-border')} />
          )}
        </div>
        <div className={cn('mt-8 flex h-12 items-end gap-0.5', isDark ? 'opacity-20' : 'opacity-30')}>
          <LoadingSpinner className="h-5 w-5" />
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col justify-between rounded-sm border p-6',
        isDark
          ? 'border-emerald-500/20 bg-gray-900 text-emerald-400'
          : 'border-aasila-border/50 bg-aasila-surface-ai',
        className,
      )}
    >
      <div>
        <div className="mb-4 flex items-start justify-between">
          <span
            className={cn(
              'text-[11px] font-mono uppercase tracking-widest',
              isDark ? 'text-emerald-400/70' : 'text-aasila-muted',
            )}
          >
            {label}
          </span>
          {icon && (
            <span className={cn('text-sm', isDark ? 'text-emerald-400' : 'text-emerald-500')}>
              {icon}
            </span>
          )}
        </div>
        <div className={cn('text-3xl font-mono font-bold', isDark ? 'text-emerald-400' : 'text-aasila-text')}>
          {value}
        </div>
        {deltaPercent !== undefined && (
          <div
            className={cn(
              'mt-1 text-[10px] font-mono',
              deltaPercent >= 0
                ? 'text-emerald-500'
                : 'text-red-500',
            )}
          >
            {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(1)}% FROM LAST SESSION
          </div>
        )}
      </div>

      {history && history.length > 0 && (
        <div className="mt-8 flex h-12 w-full items-end gap-[2px]">
          <Sparkline data={history} height={48} color={deltaPercent !== undefined && deltaPercent >= 0 ? '#10b981' : '#ef4444'} />
        </div>
      )}
    </div>
  )
})
