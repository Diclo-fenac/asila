import { useRef, useEffect } from 'react'
import { MessageBubble } from './MessageBubble'
import { MessageInput } from './MessageInput'
import { useChat } from '../../hooks/useChat'

export function ChatWindow() {
  const { messages, isStreaming, isSending, sendMessage, sendFeedback, error } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full flex-col">
      {/* Sticky header */}
      <header className="absolute right-0 top-0 z-10 flex h-[48px] w-full items-center justify-center border-b border-aasila-border/50 bg-aasila-bg-main/90 px-4 backdrop-blur-sm">
        <div className="flex w-full items-center justify-between px-4 sm:max-w-[768px] sm:px-0 sm:mx-auto">
          <div className="flex items-center gap-2 text-aasila-text">
            <h2 className="text-sm font-semibold leading-tight">Conversation</h2>
          </div>
          <div className="flex items-center text-aasila-muted" title="GovCloud Level 4 Security">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </div>
      </header>

      {/* Message list */}
      <div
        ref={scrollRef}
        className="no-scrollbar flex-1 overflow-y-auto px-4 pt-[64px] pb-[120px]"
      >
        <div className="mx-auto w-full sm:max-w-[768px] flex flex-col gap-6">
          {isEmpty && (
            <div className="flex flex-1 items-center justify-center py-20">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
                  <svg className="h-8 w-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="mb-1 text-lg font-semibold text-aasila-text">Start a Conversation</h3>
                <p className="text-sm text-aasila-muted">
                  Ask a question and get an AI-powered answer with verified sources.
                </p>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onFeedback={sendFeedback}
            />
          ))}

          {error && (
            <div className="w-full rounded-md border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-500" role="alert">
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sticky input */}
      <div className="absolute bottom-0 right-0 left-0 bg-gradient-to-t from-aasila-bg-main via-aasila-bg-main to-transparent px-4 pb-6 pt-10">
        <div className="mx-auto w-full sm:max-w-[768px]">
          <MessageInput
            onSend={sendMessage}
            isLoading={isSending || isStreaming}
          />
        </div>
      </div>
    </div>
  )
}
