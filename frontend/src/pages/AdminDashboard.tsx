import { useAnalytics } from '../hooks/useAnalytics'
import { MetricCard } from '../components/data/MetricCard'
import { ActivityLog } from '../features/admin/ActivityLog'

function TrendUpIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  )
}

function UsersIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  )
}

function ServerIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
    </svg>
  )
}

export function AdminDashboard() {
  const { metrics, activityLog, systemStatus, isLoading, isError } = useAnalytics()

  if (isError) {
    return (
      <div className="mx-auto flex max-w-7xl flex-col gap-8 p-8">
        <div className="flex items-end justify-between border-b border-aasila-border/50 pb-6">
          <div>
            <div className="mb-1 text-[10px] font-mono uppercase tracking-[0.2em] text-aasila-muted">
              System Overview / Main
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-aasila-text">Admin Dashboard</h1>
          </div>
        </div>

        <div className="rounded-md border border-red-500/30 bg-red-500/5 p-8 text-center">
          <svg className="mx-auto mb-3 h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mb-1 text-lg font-semibold text-aasila-text">Unable to load metrics</h3>
          <p className="text-sm text-aasila-muted">The analytics service may be temporarily unavailable.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-8">
      {/* Page Header */}
      <div className="flex items-end justify-between border-b border-aasila-border/50 pb-6">
        <div>
          <div className="mb-1 text-[10px] font-mono uppercase tracking-[0.2em] text-aasila-muted">
            System Overview / Main
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-aasila-text">Admin Dashboard</h1>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-aasila-muted">
          <span
            className={`h-2 w-2 rounded-full ${
              systemStatus?.status === 'operational'
                ? 'bg-emerald-500 animate-pulse'
                : systemStatus?.status === 'degraded'
                  ? 'bg-amber-500'
                  : 'bg-red-500'
            }`}
          />
          {systemStatus
            ? `${systemStatus.uptime_percent.toFixed(2)}% UPTIME`
            : 'CONNECTING...'}
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Total Queries */}
        <MetricCard
          label="Total Queries"
          value={isLoading ? '—' : (metrics?.[0]?.value ?? '0').toLocaleString()}
          deltaPercent={metrics?.[0]?.delta_percent}
          history={metrics?.[0]?.history}
          icon={<TrendUpIcon />}
          isLoading={isLoading}
          className="col-span-12 lg:col-span-4"
        />

        {/* Active Users */}
        <MetricCard
          label="Active Users"
          value={isLoading ? '—' : (metrics?.[1]?.value ?? '0').toLocaleString()}
          deltaPercent={metrics?.[1]?.delta_percent}
          history={metrics?.[1]?.history}
          icon={<UsersIcon />}
          isLoading={isLoading}
          className="col-span-12 lg:col-span-4"
        />

        {/* System Status */}
        <div className="col-span-12 flex flex-col justify-between rounded-sm border border-emerald-500/20 bg-gray-900 p-6 text-emerald-400 lg:col-span-4">
          {isLoading ? (
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="mb-2 h-3 w-24 animate-pulse rounded bg-emerald-500/20" />
                  <div className="h-6 w-40 animate-pulse rounded bg-emerald-500/20" />
                </div>
                <div className="h-4 w-4 animate-pulse rounded bg-emerald-500/20" />
              </div>
              <div className="mt-6 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-3 w-full animate-pulse rounded border-b border-emerald-500/20 pb-1" />
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest opacity-70">
                    System Status
                  </div>
                  <div className="mt-2 text-xl font-bold">
                    {systemStatus?.status === 'operational'
                      ? 'All Nodes Operational'
                      : systemStatus?.status === 'degraded'
                        ? 'Degraded Performance'
                        : 'System Outage'}
                  </div>
                </div>
                <ServerIcon />
              </div>
              {systemStatus && (
                <div className="mt-6 space-y-3">
                  <div className="flex justify-between border-b border-emerald-500/20 pb-1 text-[10px] font-mono">
                    <span>LATENCY</span>
                    <span>{systemStatus.latency_ms}ms</span>
                  </div>
                  <div className="flex justify-between border-b border-emerald-500/20 pb-1 text-[10px] font-mono">
                    <span>STORAGE</span>
                    <span>{systemStatus.storage_percent}% CAPACITY</span>
                  </div>
                  <div className="flex justify-between border-b border-emerald-500/20 pb-1 text-[10px] font-mono">
                    <span>API_LOAD</span>
                    <span className="uppercase">{systemStatus.api_load}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Activity Log */}
        <ActivityLog
          entries={activityLog ?? []}
          isLoading={isLoading}
        />

        {/* Quick Actions */}
        <div className="col-span-12 space-y-6 lg:col-span-4">
          <div className="rounded-sm border border-aasila-border/50 bg-aasila-surface-user p-6">
            <h4 className="mb-4 text-[11px] font-mono uppercase tracking-widest text-aasila-text">
              Quick Diagnostic
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                className="group flex flex-col items-center justify-center rounded-sm border border-aasila-border/50 p-4 text-aasila-text transition-all hover:border-emerald-500 hover:text-emerald-500"
              >
                <svg className="mb-2 h-5 w-5 opacity-50 transition-opacity group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-[10px] font-mono">REBOOT_NODE</span>
              </button>
              <button
                type="button"
                className="group flex flex-col items-center justify-center rounded-sm border border-aasila-border/50 p-4 text-aasila-text transition-all hover:border-emerald-500 hover:text-emerald-500"
              >
                <svg className="mb-2 h-5 w-5 opacity-50 transition-opacity group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <span className="text-[10px] font-mono">PURGE_CACHE</span>
              </button>
              <button
                type="button"
                className="group flex flex-col items-center justify-center rounded-sm border border-aasila-border/50 p-4 text-aasila-text transition-all hover:border-emerald-500 hover:text-emerald-500"
              >
                <svg className="mb-2 h-5 w-5 opacity-50 transition-opacity group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="text-[10px] font-mono">SYNC_TENANTS</span>
              </button>
              <button
                type="button"
                className="group flex flex-col items-center justify-center rounded-sm border border-aasila-border/50 p-4 text-aasila-text transition-all hover:border-emerald-500 hover:text-emerald-500"
              >
                <svg className="mb-2 h-5 w-5 opacity-50 transition-opacity group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-[10px] font-mono">SCAN_VULN</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Meta */}
      <div className="flex flex-col items-center justify-between gap-4 pt-8 text-[10px] font-mono text-aasila-muted md:flex-row">
        <div className="flex gap-6">
          <span>BUILD_VERSION: 1.0.4-STABLE</span>
          <span>KERNEL: CLOUD_OS_4.2</span>
        </div>
        <div>© 2026 AASILA DATA SYSTEMS. SECURED PROTOCOL.</div>
      </div>
    </div>
  )
}
