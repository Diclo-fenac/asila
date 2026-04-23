import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'
import { LoadingSpinner } from './LoadingSpinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  isLoading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-all',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          'active:scale-[0.98]',
          variant === 'primary' && 'bg-emerald-500 text-white hover:bg-emerald-600',
          variant === 'secondary' && 'border border-aasila-border bg-aasila-surface-user text-aasila-text hover:bg-aasila-bg-main',
          variant === 'ghost' && 'text-aasila-muted hover:bg-aasila-border/30 hover:text-aasila-text',
          variant === 'danger' && 'bg-red-500 text-white hover:bg-red-600',
          className,
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <LoadingSpinner className="h-4 w-4" />}
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'
