import { useQuery } from '@tanstack/react-query'
import { fetchMetrics, fetchActivityLog, fetchSystemStatus } from '../api/analytics'
import type { MetricPoint, ActivityLogEntry, SystemStatus } from '../types/analytics'

interface AnalyticsData {
  metrics: MetricPoint[] | undefined
  activityLog: ActivityLogEntry[] | undefined
  systemStatus: SystemStatus | undefined
  isLoading: boolean
  isError: boolean
}

export function useAnalytics(): AnalyticsData {
  const { data: metrics, isLoading: metricsLoading, isError: metricsError } = useQuery<MetricPoint[], Error>({
    queryKey: ['analytics-metrics'],
    queryFn: fetchMetrics,
    staleTime: 30 * 1000,
    retry: 1,
  })

  const { data: activityLog, isLoading: logLoading, isError: logError } = useQuery<ActivityLogEntry[], Error>({
    queryKey: ['analytics-activity'],
    queryFn: fetchActivityLog,
    staleTime: 30 * 1000,
    retry: 1,
  })

  const { data: systemStatus, isLoading: statusLoading, isError: statusError } = useQuery<SystemStatus, Error>({
    queryKey: ['analytics-status'],
    queryFn: fetchSystemStatus,
    staleTime: 15 * 1000,
    retry: 1,
  })

  return {
    metrics,
    activityLog,
    systemStatus,
    isLoading: metricsLoading || logLoading || statusLoading,
    isError: metricsError || logError || statusError,
  }
}
