import { useState } from 'react'
import { TenantCard } from './TenantCard'
import { TenantProvisioningModal } from './TenantProvisioningModal'
import { useTenantsList, useCancelProvisioning } from '../../hooks/useTenants'

export function TenantGrid() {
  const [showProvisionModal, setShowProvisionModal] = useState(false)
  const { data, isLoading, isError } = useTenantsList()
  const cancelMutation = useCancelProvisioning()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex flex-col gap-4 rounded-sm border border-aasila-border bg-aasila-surface-ai p-5">
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="h-5 w-32 animate-pulse rounded bg-aasila-border" />
                <div className="h-3 w-16 animate-pulse rounded bg-aasila-border" />
              </div>
              <div className="h-5 w-20 animate-pulse rounded bg-aasila-border" />
            </div>
            <div className="h-8 w-full animate-pulse rounded bg-aasila-border" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-md border border-red-500/30 bg-red-500/5 p-8 text-center">
        <h3 className="mb-1 text-lg font-semibold text-aasila-text">Unable to load tenants</h3>
        <p className="text-sm text-aasila-muted">Please try again later.</p>
      </div>
    )
  }

  const tenants = data?.items ?? []

  return (
    <>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {tenants.map((tenant) => (
          <TenantCard
            key={tenant.id}
            tenant={tenant}
            onCancel={(id) => cancelMutation.mutate(id)}
          />
        ))}

        {/* Add Tenant Card */}
        <button
          type="button"
          onClick={() => setShowProvisionModal(true)}
          className="flex min-h-[160px] cursor-pointer flex-col items-center justify-center gap-3 rounded-sm border-2 border-dashed border-aasila-border text-aasila-muted transition-all hover:border-emerald-500 hover:text-emerald-500"
          aria-label="Add new tenant"
        >
          <svg className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs font-bold uppercase tracking-widest">Add Custom Tenant</span>
        </button>
      </div>

      <TenantProvisioningModal isOpen={showProvisionModal} onClose={() => setShowProvisionModal(false)} />
    </>
  )
}
