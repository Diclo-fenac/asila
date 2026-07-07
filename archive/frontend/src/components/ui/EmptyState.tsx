import type { ReactNode } from 'react'
import { FolderOpen } from 'lucide-react'
import { cn } from '../../utils/cn'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-aasila-border/60 bg-aasila-surface-low/30 p-8 text-center animate-in fade-in duration-500", className)}>
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-accent/10 text-brand-accent">
        {icon || <FolderOpen className="h-8 w-8" />}
      </div>
      <h3 className="mb-1 text-lg font-semibold text-aasila-text">{title}</h3>
      <p className="mb-6 max-w-sm text-sm text-aasila-muted">{description}</p>
      {action && <div>{action}</div>}
    </div>
  )
}
