import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { useInviteUser } from '../../hooks/useUsers'

const inviteSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  role: z.enum(['admin', 'analyst', 'viewer']),
})

type InviteFormData = z.infer<typeof inviteSchema>

interface UserInviteModalProps {
  isOpen: boolean
  onClose: () => void
}

export function UserInviteModal({ isOpen, onClose }: UserInviteModalProps) {
  const [success, setSuccess] = useState(false)
  const inviteMutation = useInviteUser()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      name: '',
      email: '',
      role: 'viewer',
    },
  })

  const onSubmit = async (data: InviteFormData) => {
    await inviteMutation.mutateAsync(data)
    setSuccess(true)
    setTimeout(() => {
      setSuccess(false)
      reset()
      onClose()
    }, 2000)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Invite User">
      {success ? (
        <div className="py-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
            <svg className="h-6 w-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="mb-1 text-lg font-semibold text-aasila-text">Invitation Sent</h3>
          <p className="text-sm text-aasila-muted">An invite link has been sent to the user&apos;s email.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          <Input
            id="invite_name"
            label="Full Name"
            placeholder="Jane Doe"
            {...register('name')}
            error={errors.name?.message}
          />

          <Input
            id="invite_email"
            type="email"
            label="Email Address"
            placeholder="jane@company.com"
            {...register('email')}
            error={errors.email?.message}
          />

          <Select
            id="invite_role"
            label="Role"
            {...register('role')}
          >
            <option value="viewer">Viewer — Read-only access</option>
            <option value="analyst">Analyst — Query and document access</option>
            <option value="admin">Admin — Full access</option>
          </Select>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={inviteMutation.isPending}>
              Send Invite
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
