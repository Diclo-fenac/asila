import { Select } from '../../components/ui/Select'
import { useTenantsList } from '../../hooks/useTenants'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

interface TenantSelectorProps {
  value: string
  onChange: (value: string) => void
  error?: string
}

export function TenantSelector({ value, onChange, error }: TenantSelectorProps) {
  const { data, isLoading, isError } = useTenantsList()
  const tenants = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-1.5">
        <span className="block text-[11px] font-medium uppercase tracking-wider text-aasila-muted">
          Organization / Tenant
        </span>
        <div className="flex items-center gap-2 rounded-md border border-aasila-border bg-aasila-surface-user px-3 py-2.5">
          <LoadingSpinner className="h-4 w-4" />
          <span className="text-sm text-aasila-muted">Loading tenants...</span>
        </div>
      </div>
    )
  }

  if (isError) {
    // Fallback to hardcoded options if API fails
    return (
      <Select
        label="Organization / Tenant"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        error={error}
        aria-describedby="tenant-help"
      >
        <option value="global">Global Operations Center</option>
        <option value="eu-west">EU West Distribution</option>
        <option value="ap-east">Asia Pacific Research</option>
      </Select>
    )
  }

  if (!tenants || tenants.length === 0) {
    return (
      <Select
        label="Organization / Tenant"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        error={error}
      >
        <option value="default">Default Tenant</option>
      </Select>
    )
  }

  return (
    <Select
      label="Organization / Tenant"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      error={error}
      aria-describedby="tenant-help"
    >
      {tenants.map((tenant) => (
        <option key={tenant.id} value={tenant.id}>
          {tenant.name} ({tenant.status})
        </option>
      ))}
    </Select>
  )
}
