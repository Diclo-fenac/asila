export type TenantStatus = 'active' | 'provisioning' | 'offline' | 'suspended'

export interface Tenant {
  id: string
  name: string
  status: TenantStatus
  created_at: string
  updated_at: string
  health_index?: number
  last_sync?: string
  user_count?: number
}

export interface CreateTenantRequest {
  name: string
  admin_email: string
  admin_name: string
  admin_password: string
}

export interface TenantProvisioningProgress {
  tenant_id: string
  step: string
  progress: number // 0-100
  estimated_remaining_seconds?: number
}
