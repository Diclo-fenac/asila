import { useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MessageBubble } from './MessageBubble'
import { MessageInput } from './MessageInput'
import { useChat } from '../../hooks/useChat'
import { useConversations } from '../../hooks/useConversations'

export function ChatWindow() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { createConversation } = useConversations()
  const { messages, isStreaming, isSending, sendMessage, sendFeedback, error } = useChat(conversationId || null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const isEmpty = messages.length === 0

  const handleSend = async (content: string) => {
    let targetId = conversationId
    if (!targetId) {
      const newConv = await createConversation()
      targetId = newConv.id
      navigate(`/chat/${targetId}`, { replace: true })
    }
    await sendMessage(content, targetId)
  }

  return (
    <div className="relative flex h-full flex-col bg-[var(--color-neutral-50)] overflow-hidden">
      {/* Clean Minimal Background */}
      <div className="absolute inset-0 pointer-events-none bg-grid-aasila-border/[0.05] [mask-image:linear-gradient(to_bottom,white,transparent)]" />

      {/* Sticky header */}
      <header className="absolute right-0 top-0 z-10 flex h-[48px] w-full items-center justify-center border-b border-aasila-border glass-panel px-4">
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
            <div className="flex flex-1 items-center justify-center py-10 lg:py-20">
              <div className="w-full max-w-2xl px-4">
                <div className="text-center mb-10">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-accent/10 shadow-sm border border-brand-accent/20">
                    <svg className="h-8 w-8 text-brand-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L4.2 15.3m15.6 0v1.47a2.25 2.25 0 01-1.13 1.954l-5.36 3.1a2.25 2.25 0 01-2.34 0l-5.36-3.1a2.25 2.25 0 01-1.13-1.954V15.3c0-1.42 1.138-2.617 2.582-2.923l1.23-.263a11.208 11.208 0 014.376 0l1.23.263c1.444.306 2.582 1.503 2.582 2.923v1.47z" />
                    </svg>
                  </div>
                  <h3 className="mb-2 text-2xl font-semibold text-aasila-text tracking-tight">How can I help you today?</h3>
                  <p className="text-sm text-aasila-muted">Ask questions, analyze documents, or fetch verified data.</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {[
                    { title: "Analyze Tenant Data", desc: "Show me the usage metrics for the active tenant", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
                    { title: "Review Security Policy", desc: "Summarize the latest SOC2 compliance requirements", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
                    { title: "Search Knowledge Base", desc: "Find documents related to the recent Q3 API migration", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" },
                    { title: "Draft a Report", desc: "Write an executive summary of current platform usage", icon: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" }
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(prompt.desc)}
                      className="group flex flex-col items-start p-4 text-left rounded-xl border border-aasila-border/50 bg-aasila-surface shadow-sm hover:shadow-md hover:border-brand-accent/30 transition-all duration-200"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className="p-1.5 rounded-lg bg-aasila-surface-user text-brand-accent">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d={prompt.icon} />
                          </svg>
                        </div>
                        <span className="font-semibold text-sm text-aasila-text">{prompt.title}</span>
                      </div>
                      <span className="text-xs text-aasila-muted group-hover:text-aasila-text transition-colors">
                        "{prompt.desc}"
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onFeedback={(id, feedback) => { void sendFeedback(id, feedback) }}
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
      <div className="fixed bottom-6 left-4 right-4 lg:left-72 lg:right-8 z-50 flex justify-center pointer-events-none">
        <div className="w-full sm:max-w-[768px] rounded-2xl glass-panel-floating border border-aasila-border shadow-2xl p-2 pointer-events-auto transition-all duration-300">
          <MessageInput
            onSend={(content) => { void handleSend(content) }}
            isLoading={isSending || isStreaming}
          />
        </div>
      </div>
    </div>
  )
}
