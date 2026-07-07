import { TenantGrid } from '../features/tenants/TenantGrid'
import { useTenantsList } from '../hooks/useTenants'
import { MetricCard } from '../components/data/MetricCard'
import type { Tenant } from '../types/tenant'

export function PlatformTenantManagement() {
  const { data, isLoading } = useTenantsList()

  const tenants = data?.items ?? []
  const avgHealth = tenants.length > 0
    ? tenants.reduce((sum: number, t: Tenant) => sum + (t.health_index ?? 0), 0) / tenants.length
    : 0

  return (
    <div className="w-full p-8">
      {/* Page Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="mb-1 text-[24px] font-semibold text-aasila-text">Platform Tenant Management</h2>
          <p className="text-sm text-aasila-muted">Onboard and manage isolated organizational environments.</p>
        </div>
        <div className="flex items-center gap-3 rounded-sm border border-aasila-border bg-aasila-bg-sidebar px-4 py-2 text-sm text-aasila-muted">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Add tenants from the grid below
        </div>
      </div>

      {/* Stats */}
      <div className="mb-10 grid grid-cols-12 gap-6">
        <MetricCard
          label="Total Clusters"
          value={tenants.length.toString()}
          className="col-span-12 lg:col-span-8"
        />
        <MetricCard
          label="Health Index"
          value={isLoading ? '—' : `${avgHealth.toFixed(1)}%`}
          className="col-span-12 lg:col-span-4"
        />
      </div>

      {/* Tenant Grid */}
      <TenantGrid />
    </div>
  )
}
