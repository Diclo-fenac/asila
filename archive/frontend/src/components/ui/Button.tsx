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
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-accent focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          'active:scale-95',
          variant === 'primary' && 'bg-aasila-text text-aasila-bg-main hover:bg-aasila-text/90',
          variant === 'secondary' && 'border border-aasila-border bg-transparent text-aasila-text hover:bg-aasila-muted/10',
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
