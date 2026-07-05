import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDocuments, deleteDocument, uploadDocument } from '../api/documents'
import { useToast } from './useToast'

// Polling interval in ms for refetching when there are processing documents
const POLLING_INTERVAL = 5000

export function useDocumentsList() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
    // Poll every 5s to refresh statuses, or we can leave it off and manually invalidate
    refetchInterval: (query) => {
      // If any document is "pending", we should poll
      const hasPending = query.state.data?.some(d => d.status !== 'ready')
      return hasPending ? POLLING_INTERVAL : false
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      addToast('Document deleted', 'success')
    },
    onError: () => {
      addToast('Failed to delete document', 'error')
    }
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  return useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) => uploadDocument(file, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      addToast('Document uploaded successfully. Processing...', 'success')
    },
    onError: () => {
      addToast('Failed to upload document', 'error')
    }
  })
}
