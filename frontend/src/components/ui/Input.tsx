import { forwardRef } from 'react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, type = 'text', ...props }, ref) => {
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
        <input
          ref={ref}
          id={id}
          type={type}
          className={cn(
            'w-full rounded-md border border-aasila-border bg-aasila-surface-user px-3 py-2.5 text-sm text-aasila-text',
            'placeholder:text-aasila-muted/50',
            'focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500',
            'transition-all',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
            className,
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-500" role="alert">{error}</p>}
      </div>
    )
  },
)

Input.displayName = 'Input'
