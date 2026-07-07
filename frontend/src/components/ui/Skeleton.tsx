import { cn } from '../../utils/cn'

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-aasila-border/40', className)}
      {...props}
    />
  )
}
