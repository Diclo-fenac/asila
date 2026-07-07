import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadDocument } from '../api/documents'
import { useToast } from './useToast'


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
