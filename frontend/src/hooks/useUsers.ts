import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchUsers, inviteUser, updateUserRole, deleteUser } from '../api/users'
import type { UserRole } from '../types/auth'
import type { PaginationParams } from '../types/api'
import { useToast } from './useToast'

export function useUsersList(params: PaginationParams = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => fetchUsers(params),
    staleTime: 30 * 1000,
    retry: 1,
  })
}

export function useInviteUser() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: ({ email, role, name }: { email: string; role: UserRole; name: string }) =>
      inviteUser(email, role, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast('Invitation sent successfully', 'success')
    },
    onError: () => {
      addToast('Failed to send invitation', 'error')
    },
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) => updateUserRole(userId, role),
    onSuccess: (_, { role }) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast(`Role updated to ${role}`, 'success')
    },
    onError: () => {
      addToast('Failed to update role', 'error')
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast('User deleted', 'success')
    },
  })
}
