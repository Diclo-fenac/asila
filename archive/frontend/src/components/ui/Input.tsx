import { forwardRef, type ReactNode } from 'react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  rightElement?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, type = 'text', rightElement, ...props }, ref) => {
    const errorId = id ? `${id}-error` : undefined

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
        <div className="relative w-full">
          <input
            ref={ref}
            id={id}
            type={type}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : undefined}
            className={cn(
              'w-full rounded-md border border-aasila-border bg-aasila-surface-user px-3 py-2.5 text-sm text-aasila-text',
              'placeholder:text-aasila-muted/50',
              'focus:border-brand-accent focus:outline-none focus:ring-1 focus:ring-brand-accent',
              'transition-all',
              error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
              rightElement && 'pr-10',
              className,
            )}
            {...props}
          />
          {rightElement && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3">
              {rightElement}
            </div>
          )}
        </div>
        {error && (
          <p id={errorId} className="text-xs text-red-500" role="alert" aria-live="polite">
            {error}
          </p>
        )}
      </div>
    )
  },
)

Input.displayName = 'Input'
