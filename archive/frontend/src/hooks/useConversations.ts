import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getConversations, createConversation, deleteConversation, renameConversation } from '../api/conversations'
import type { Conversation } from '../api/conversations'

export function useConversations() {
  const queryClient = useQueryClient()

  const { data: conversations = [], isLoading, error } = useQuery<Conversation[], Error>({
    queryKey: ['conversations'],
    queryFn: getConversations,
  })

  const createMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (newConv) => {
      queryClient.setQueryData<Conversation[]>(['conversations'], (old) => [newConv, ...(old || [])])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<Conversation[]>(['conversations'], (old) => 
        old?.filter(c => c.id !== deletedId) || []
      )
    },
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameConversation(id, title),
    onSuccess: (updatedConv) => {
      queryClient.setQueryData<Conversation[]>(['conversations'], (old) => 
        old?.map(c => c.id === updatedConv.id ? updatedConv : c) || []
      )
    },
  })

  return {
    conversations,
    isLoading,
    error,
    createConversation: createMutation.mutateAsync,
    deleteConversation: deleteMutation.mutateAsync,
    renameConversation: renameMutation.mutateAsync,
    isCreating: createMutation.isPending,
  }
}
