import { apiClient } from './client'
import type { MetricPoint, ActivityLogEntry, SystemStatus } from '../types/analytics'

export async function fetchMetrics(days: number = 30): Promise<MetricPoint[]> {
  const response = await apiClient.get<MetricPoint[]>(`/analytics/metrics?days=${days}`)
  return response.data
}

export async function fetchActivityLog(): Promise<ActivityLogEntry[]> {
  const response = await apiClient.get<ActivityLogEntry[]>('/analytics/activity')
  return response.data
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await apiClient.get<SystemStatus>('/analytics/status')
  return response.data
}
