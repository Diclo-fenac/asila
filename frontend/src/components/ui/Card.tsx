import { forwardRef, type HTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'bg-surface-container-lowest rounded-xl p-6 ambient-shadow border border-outline-variant/20',
        className
      )}
      {...props}
    />
  )
)

Card.displayName = 'Card'
