export type IngestionStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface Document {
  id: string
  tenant_id: string
  title: string
  filename: string
  file_type: string
  file_size: number
  status: IngestionStatus
  uploaded_at: string
  processed_at: string | null
  error_message: string | null
}

export interface DocumentUploadResponse {
  id: string
  filename: string
  status: IngestionStatus
}
