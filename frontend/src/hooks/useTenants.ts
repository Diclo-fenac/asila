import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTenants, createTenant, deleteTenant, cancelProvisioning } from '../api/tenants'
import type { CreateTenantRequest } from '../types/tenant'
import { useToast } from './useToast'

export function useTenantsList(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['tenants', page, pageSize],
    queryFn: () => fetchTenants({ page, page_size: pageSize }),
    staleTime: 30 * 1000,
    retry: 1,
  })
}

export function useCreateTenant() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: (data: CreateTenantRequest) => createTenant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      addToast('Tenant provisioned successfully', 'success')
    },
    onError: () => {
      addToast('Failed to create tenant', 'error')
    },
  })
}

export function useDeleteTenant() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: deleteTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      addToast('Tenant deleted', 'success')
    },
  })
}

export function useCancelProvisioning() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: cancelProvisioning,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      addToast('Provisioning cancelled', 'info')
    },
  })
}
