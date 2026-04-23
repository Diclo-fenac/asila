import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { useCreateTenant } from '../../hooks/useTenants'

const createTenantSchema = z.object({
  name: z.string().min(2, 'Tenant name must be at least 2 characters'),
  admin_email: z.string().email('Please enter a valid admin email'),
  admin_name: z.string().min(2, 'Admin name must be at least 2 characters'),
  admin_password: z.string().min(8, 'Password must be at least 8 characters'),
})

type CreateTenantFormData = z.infer<typeof createTenantSchema>

interface TenantProvisioningModalProps {
  isOpen: boolean
  onClose: () => void
}

export function TenantProvisioningModal({ isOpen, onClose }: TenantProvisioningModalProps) {
  const [success, setSuccess] = useState(false)
  const createMutation = useCreateTenant()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CreateTenantFormData>({
    resolver: zodResolver(createTenantSchema),
    defaultValues: {
      name: '',
      admin_email: '',
      admin_name: '',
      admin_password: '',
    },
  })

  const onSubmit = async (data: CreateTenantFormData) => {
    await createMutation.mutateAsync(data)
    setSuccess(true)
    setTimeout(() => {
      setSuccess(false)
      reset()
      onClose()
    }, 2000)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Onboard New Tenant" size="lg">
      {success ? (
        <div className="py-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
            <svg className="h-6 w-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="mb-1 text-lg font-semibold text-aasila-text">Tenant Provisioning</h3>
          <p className="text-sm text-aasila-muted">The new tenant is being provisioned. You can monitor progress from the tenant grid.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          <Input
            id="tenant_name"
            label="Tenant Name"
            placeholder="Stark Industries"
            {...register('name')}
            error={errors.name?.message}
          />

          <Input
            id="admin_name"
            label="Admin Name"
            placeholder="Tony Stark"
            {...register('admin_name')}
            error={errors.admin_name?.message}
          />

          <Input
            id="admin_email"
            type="email"
            label="Admin Email"
            placeholder="tony@stark.com"
            {...register('admin_email')}
            error={errors.admin_email?.message}
          />

          <Input
            id="admin_password"
            type="password"
            label="Admin Password"
            placeholder="••••••••"
            {...register('admin_password')}
            error={errors.admin_password?.message}
          />

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Provision Tenant
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
