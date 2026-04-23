import { forwardRef } from 'react'
import type { SelectHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className, children, id, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={id}
            className="block text-[11px] font-medium uppercase tracking-wider text-aasila-muted"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          className={cn(
            'w-full rounded-md border border-aasila-border bg-aasila-surface-user px-3 py-2.5 text-sm text-aasila-text',
            'focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500',
            'transition-all',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
            className,
          )}
          {...props}
        >
          {children}
        </select>
        {error && <p className="text-xs text-red-500" role="alert">{error}</p>}
      </div>
    )
  },
)

Select.displayName = 'Select'
