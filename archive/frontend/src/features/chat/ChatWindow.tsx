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



      {/* Message list */}
      <div
        ref={scrollRef}
        className="no-scrollbar flex-1 overflow-y-auto px-4 pt-8 pb-[140px]"
      >
        <div className="mx-auto w-full sm:max-w-[800px] flex flex-col gap-6">
          {isEmpty && (
            <div className="flex flex-1 items-center justify-center pt-2 pb-6 lg:pt-6 lg:pb-10">
              <div className="w-full max-w-2xl px-4">
                <div className="text-center mb-6">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-accent text-white shadow-sm border border-brand-accent/20">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <h3 className="mb-2 text-2xl font-black text-aasila-text tracking-tight">AASILA Lease Intelligence</h3>
                  <p className="text-[14px] text-aasila-muted font-medium">Upload a lease agreement or ask a question to analyze tenant obligations, identify risks, and compare against policy.</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {[
                    { title: "Find risky clauses", desc: "Scan this lease for potential liability or unusual terms", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" },
                    { title: "Summarize obligations", desc: "Extract all tenant maintenance and financial responsibilities", icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
                    { title: "Compare with policy", desc: "Check if this contract complies with standard operating rules", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
                    { title: "Analyze new lease", desc: "Upload a new document to begin extraction", icon: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12", isPrimary: true }
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(prompt.desc)}
                      className={`group flex flex-col items-start p-3 text-left rounded-lg border transition-all duration-150 ${prompt.isPrimary ? 'border-brand-accent/40 bg-brand-accent-tint text-brand-accent' : 'border-aasila-border bg-white hover:border-brand-accent/40 hover:bg-aasila-surface-user'}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`flex items-center justify-center`}>
                          <svg className={`w-4 h-4 ${prompt.isPrimary ? 'text-brand-accent' : 'text-aasila-muted group-hover:text-brand-accent transition-colors'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d={prompt.icon} />
                          </svg>
                        </div>
                        <span className={`font-semibold text-[13px] ${prompt.isPrimary ? 'text-brand-accent' : 'text-aasila-text'}`}>{prompt.title}</span>
                      </div>
                      <span className="text-[12px] leading-tight text-aasila-muted group-hover:text-aasila-text transition-colors">
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
        <div className="w-full sm:max-w-[800px] pointer-events-auto">
          <MessageInput
            onSend={(content) => { void handleSend(content) }}
            isLoading={isSending || isStreaming}
          />
        </div>
      </div>
    </div>
  )
}
