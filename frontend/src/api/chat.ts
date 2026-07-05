import { apiClient, API_URL, getStoredTenantId } from './client'
import type { Message, Citation, ChatResponse } from '../types/chat'
import { useAuthStore } from '../store/useAuthStore'
import { globalToast } from '../components/ui/Toast'
import axios from 'axios'

export async function sendMessage(content: string): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/chat/query', {
    query: content,
  })
  return response.data
}

export function streamResponse(
  content: string,
  conversationId: string | null,
  onChunk: (chunk: string) => void,
  onDone: (fullText: string, citations: Citation[]) => void,
  onError: (error: Error) => void,
): AbortController {
  const controller = new AbortController()

  const executeStream = async (isRetry = false) => {
    const tenantId = getStoredTenantId()

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (tenantId) headers['X-Tenant-Id'] = tenantId
    
    const body: Record<string, any> = { query: content }
    if (conversationId) body.conversation_id = conversationId

    try {
      const response = await fetch(`${API_URL}/chat/query/stream`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (response.status === 401 && !isRetry) {
        // Attempt to refresh the token using HttpOnly cookies
        try {
          await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true })
          // Retry the stream request once
          return executeStream(true)
        } catch (refreshError) {
          useAuthStore.getState().clearAuth()
          throw new Error('Session expired. Please log in again.')
        }
      }

      if (!response.ok) {
        if (response.status >= 500) {
          globalToast('Server error: An unexpected error occurred on our end.', 'error')
        } else if (response.status === 403) {
          globalToast('Access denied: You do not have permission.', 'warning')
        }
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
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        if (err.message.includes('fetch')) {
          globalToast('Network error: Unable to connect to the server.', 'error')
        }
        onError(err)
      } else if (!(err instanceof Error)) {
        onError(new Error(String(err)))
      }
    }
  }

  // Start the stream
  executeStream()

  return controller
}

export async function getConversationHistory(conversationId?: string): Promise<Message[]> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ''
  const response = await apiClient.get<Message[]>(`/chat/query/history${params}`)
  return response.data
}

export async function sendFeedback(messageId: string, feedback: 'positive' | 'negative'): Promise<{ success: boolean }> {
  const response = await apiClient.post<{ success: boolean }>(`/chat/query/feedback`, {
    message_id: messageId,
    feedback,
  })
  return response.data
}
