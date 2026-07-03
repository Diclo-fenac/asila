import { apiClient } from './client'
import type { Document } from '../types/document'

export async function fetchDocuments(): Promise<Document[]> {
  const { data } = await apiClient.get<Document[]>('/documents/')
  return data
}
