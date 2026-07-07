export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  citations?: Citation[]
  feedback?: 'positive' | 'negative'
}

export interface Citation {
  document_id: string
  document_title: string
  chunk_text: string
  page_number?: number
  score: number
}

export interface ChatResponse {
  message: Message
  query_id: string
  processing_time_ms: number
}
