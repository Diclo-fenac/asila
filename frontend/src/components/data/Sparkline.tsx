import { useMemo, memo } from 'react'
import { cn } from '../../utils/cn'

interface SparklineProps {
  data: number[]
  className?: string
  color?: string
  height?: number
}

export const Sparkline = memo(function Sparkline({ data, className, color = '#10b981', height = 48 }: SparklineProps) {
  const path = useMemo(() => {
    if (data.length === 0) return ''

    const max = Math.max(...data, 1)
    const min = Math.min(...data, 0)
    const range = max - min || 1
    const width = data.length * 8 // 8px per data point
    const padding = 2

    const points = data.map((value, i) => {
      const x = (i / (data.length - 1 || 1)) * (width - padding * 2) + padding
      const y = height - padding - ((value - min) / range) * (height - padding * 2)
      return `${x},${y}`
    })

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p}`).join(' ')

    // Area fill
    const lastX = points[points.length - 1]?.split(',')[0] ?? '0'
    const firstX = points[0]?.split(',')[0] ?? '0'
    const areaPath = `${linePath} L ${lastX},${height} L ${firstX},${height} Z`

    return { linePath, areaPath, width }
  }, [data, height])

  if (!path || data.length === 0) return null

  return (
    <svg
      className={cn('w-full', className)}
      viewBox={`0 0 ${path.width} ${height}`}
      fill="none"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path d={path.areaPath} fill={color} opacity={0.15} />
      <path
        d={path.linePath}
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Last point dot */}
      {(() => {
        const lastPoint = path.linePath.split(' ').slice(-1)[0]
        const [cx, cy] = lastPoint.split(',').map(Number)
        return <circle cx={cx} cy={cy} r={3} fill={color} />
      })()}
    </svg>
  )
})
