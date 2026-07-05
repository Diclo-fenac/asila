import { apiClient } from './client'
import type { Document } from '../types/document'

export async function fetchDocuments(): Promise<Document[]> {
  const { data } = await apiClient.get<Document[]>('/documents/')
  return data
}

export async function deleteDocument(id: string): Promise<{ msg: string }> {
  const { data } = await apiClient.delete<{ msg: string }>(`/documents/${id}`)
  return data
}

export async function uploadDocument(file: File, title: string): Promise<{ job_id: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', title)
  
  const { data } = await apiClient.post<{ job_id: string; status: string }>('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    }
  })
  return data
}
