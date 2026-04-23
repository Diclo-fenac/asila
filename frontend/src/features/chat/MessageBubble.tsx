import { memo } from 'react'
import { type Message } from '../../types/chat'
import { cn } from '../../utils/cn'

interface MessageBubbleProps {
  message: Message
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export const MessageBubble = memo(function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className="relative group max-w-[85%] sm:max-w-[80%]">
        {/* User bubble */}
        {isUser ? (
          <div className="rounded-md bg-aasila-surface-user px-4 py-3 text-[15px] leading-relaxed text-aasila-text">
            {message.content}
          </div>
        ) : (
          /* AI bubble */
          <div className="rounded-md border border-aasila-border/30 bg-aasila-surface-ai p-5 text-[15px] leading-relaxed text-aasila-text shadow-sm">
            {/* Content */}
            {message.content ? (
              <div className="markdown-body whitespace-pre-wrap">{message.content}</div>
            ) : (
              <span className="animate-pulse text-lg font-bold text-emerald-500">&gt; _</span>
            )}

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <div className="mt-4 border-t border-aasila-border/30 pt-3">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-aasila-muted">
                  Sources
                </p>
                <div className="flex flex-wrap gap-2">
                  {message.citations.map((citation, i) => (
                    <div
                      key={i}
                      className="rounded-sm border border-aasila-border bg-aasila-bg-sidebar px-2 py-1 text-[11px] text-aasila-text"
                      title={citation.chunk_text}
                    >
                      {citation.document_title}
                      {citation.page_number ? ` (p.${citation.page_number})` : ''}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Utility row (hover) */}
            {message.content && (
              <div className="absolute right-2 top-2 flex items-center gap-1 rounded-sm border border-aasila-border bg-aasila-surface-ai p-1 opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(message.content)}
                  className="rounded-sm p-1 text-aasila-muted transition-colors hover:bg-aasila-bg-main hover:text-aasila-text"
                  title="Copy"
                  aria-label="Copy message"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => onFeedback?.(message.id, 'positive')}
                  className={cn(
                    'rounded-sm p-1 transition-colors hover:bg-aasila-bg-main',
                    message.feedback === 'positive'
                      ? 'text-emerald-500'
                      : 'text-aasila-muted hover:text-aasila-text',
                  )}
                  title="Helpful"
                  aria-label="Mark as helpful"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h4.764a2 2 0 011.789 2.894l3.5 7A2 2 0 0015.263 21h4.017c.163 0 .326-.02.485-.06L23 20" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => onFeedback?.(message.id, 'negative')}
                  className={cn(
                    'rounded-sm p-1 transition-colors hover:bg-aasila-bg-main',
                    message.feedback === 'negative'
                      ? 'text-red-500'
                      : 'text-aasila-muted hover:text-aasila-text',
                  )}
                  title="Not helpful"
                  aria-label="Mark as not helpful"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m0 0v5m0-5h2a2 2 0 012 2v6a2 2 0 01-2 2h-4.764a2 2 0 01-1.789-2.894l-3.5-7A2 2 0 008.736 3H4.719c-.163 0-.326.02-.485.06L1 4" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className={cn(
          'mt-1 text-[10px] font-mono text-aasila-muted',
          isUser ? 'text-right' : 'text-left',
        )}>
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  )
})
