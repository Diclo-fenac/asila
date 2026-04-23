import { apiClient } from './client'
import type { Message, Citation, ChatResponse } from '../types/chat'

export async function sendMessage(content: string): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/query', {
    query: content,
  })
  return response.data
}

export function streamResponse(
  content: string,
  onChunk: (chunk: string) => void,
  onDone: (fullText: string, citations: Citation[]) => void,
  onError: (error: Error) => void,
): AbortController {
  const controller = new AbortController()
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  const getStoredAccessToken = (): string | null => {
    try {
      const auth = localStorage.getItem('aasila_auth')
      if (auth) return JSON.parse(auth)?.access_token ?? null
    } catch {
      return null
    }
    return null
  }

  const getStoredTenantId = (): string | null => {
    try {
      const auth = localStorage.getItem('aasila_auth')
      if (auth) return JSON.parse(auth)?.tenant?.id ?? null
    } catch {
      return null
    }
    return null
  }

  const token = getStoredAccessToken()
  const tenantId = getStoredTenantId()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) headers.Authorization = `Bearer ${token}`
  if (tenantId) headers['X-Tenant-Id'] = tenantId

  fetch(`${API_URL}/query/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query: content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Stream failed: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('ReadableStream not supported')
      }

      const decoder = new TextDecoder()
      let fullText = ''
      const citations: Citation[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })

        // Parse SSE lines
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6))
              if (parsed.type === 'chunk' && parsed.content) {
                fullText += parsed.content
                onChunk(parsed.content)
              } else if (parsed.type === 'done') {
                if (parsed.citations) citations.push(...parsed.citations)
              } else if (parsed.type === 'error') {
                throw new Error(parsed.message ?? 'Stream error')
              }
            } catch (e) {
              // If it's not JSON, treat it as raw text chunk
              if (!(e instanceof SyntaxError)) throw e
              fullText += line.slice(6)
              onChunk(line.slice(6))
            }
          }
        }
      }

      onDone(fullText, citations)
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err instanceof Error ? err : new Error(String(err)))
      }
    })

  return controller
}

export async function getConversationHistory(conversationId?: string): Promise<Message[]> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ''
  const response = await apiClient.get<Message[]>(`/query/history${params}`)
  return response.data
}

export async function sendFeedback(messageId: string, feedback: 'positive' | 'negative'): Promise<{ success: boolean }> {
  const response = await apiClient.post<{ success: boolean }>(`/query/feedback`, {
    message_id: messageId,
    feedback,
  })
  return response.data
}
