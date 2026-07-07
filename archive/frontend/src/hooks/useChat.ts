import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { Message } from '../types/chat'
import { streamResponse, getConversationHistory, sendFeedback } from '../api/chat'

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  currentText: string
  isSending: boolean
  sendMessage: (content: string, overrideConvId?: string) => Promise<void>
  sendFeedback: (messageId: string, feedback: 'positive' | 'negative') => Promise<void>
  abortStream: () => void
  error: string | null
}

export function useChat(conversationId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentText, setCurrentText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const streamControllerRef = useRef<AbortController | null>(null)
  const queryClient = useQueryClient()

  // Reset messages when conversation changes
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [conversationId])

  // Load conversation history
  const { data: history } = useQuery<Message[], Error>({
    queryKey: ['chat-history', conversationId],
    queryFn: () => getConversationHistory(conversationId || undefined),
    staleTime: Infinity,
    retry: 1,
    enabled: !!conversationId, // Only fetch if we have a conversationId selected
  })

  // Initialize messages from history
  useEffect(() => {
    if (history && messages.length === 0) {
      setMessages(history)
    }
  }, [history, messages.length])

  const handleSendMessage = useCallback(async (content: string, overrideConvId?: string) => {
    if (!content.trim() || isStreaming) return

    setError(null)
    setIsSending(true)
    
    const targetConvId = overrideConvId || conversationId

    // Optimistic: add user message immediately
    const userMessage: Message = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setCurrentText('')
    setIsStreaming(true)
    setIsSending(false)

    // Create placeholder for AI response
    const assistantMessageId = `local-ai-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      },
    ])

    try {
      const controller = streamResponse(
        content.trim(),
        targetConvId,
        // onChunk
        (chunk) => {
          setCurrentText((prev) => prev + chunk)
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: m.content + chunk }
                : m,
            ),
          )
        },
        // onDone
        (fullText, citations) => {
          setIsStreaming(false)
          setCurrentText('')
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: fullText, citations }
                : m,
            ),
          )
          // Invalidate history query so it refetches
          queryClient.invalidateQueries({ queryKey: ['chat-history', targetConvId] })
        },
        // onError
        (err) => {
          setIsStreaming(false)
          setCurrentText('')
          setError(err.message)
          // Remove the failed assistant message
          setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId))
        },
      )

      streamControllerRef.current = controller
    } catch {
      setIsStreaming(false)
      setError('Failed to send message')
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId))
    }
  }, [isStreaming, queryClient, conversationId])

  const handleSendFeedback = useCallback(async (messageId: string, feedback: 'positive' | 'negative') => {
    try {
      await sendFeedback(messageId, feedback)
      // Optimistic update
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, feedback } : m,
        ),
      )
    } catch {
      // Silently fail — feedback is non-critical
    }
  }, [])

  const abortStream = useCallback(() => {
    streamControllerRef.current?.abort()
    setIsStreaming(false)
    setCurrentText('')
  }, [])

  return {
    messages,
    isStreaming,
    currentText,
    isSending,
    sendMessage: handleSendMessage,
    sendFeedback: handleSendFeedback,
    abortStream,
    error,
  }
}
