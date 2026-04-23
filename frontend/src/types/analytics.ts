export interface MetricPoint {
  label: string
  value: number
  delta_percent: number
  history: number[] // last 7 data points for sparkline
}

export interface ActivityLogEntry {
  id: string
  user: string
  action: string
  target: string
  timestamp: string
  severity: 'info' | 'warning' | 'error'
}

export interface SystemStatus {
  status: 'operational' | 'degraded' | 'outage'
  latency_ms: number
  storage_percent: number
  api_load: 'stable' | 'elevated' | 'critical'
  uptime_percent: number
}
