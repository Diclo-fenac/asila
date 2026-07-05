import { memo } from 'react'
import { type Message } from '../../types/chat'
import { cn } from '../../utils/cn'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PrismAsyncLight as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

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
          <div className="rounded-2xl rounded-tr-sm bg-aasila-text px-4 py-3 text-[15px] leading-relaxed text-aasila-bg-main shadow-sm">
            {message.content}
          </div>
        ) : (
          /* AI bubble (Clean & Professional Apple/Stripe Style) */
          <div className="rounded-2xl rounded-tl-sm border border-aasila-border/50 bg-aasila-surface p-5 text-[15px] leading-relaxed text-aasila-text shadow-sm ring-1 ring-black/5">
            {/* Content */}
            {message.content ? (
              <div className="prose prose-sm prose-neutral max-w-none break-words">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code(props) {
                      const { children, className, node, ref, ...rest } = props
                      const match = /language-(\w+)/.exec(className || '')
                      return match ? (
                        <div className="relative group/code mt-4 mb-4 rounded-md overflow-hidden border border-aasila-border/50">
                          <div className="flex items-center justify-between bg-neutral-900 px-3 py-1.5 text-xs font-mono text-neutral-400">
                            <span>{match[1]}</span>
                            <button
                              onClick={() => navigator.clipboard.writeText(String(children).replace(/\n$/, ''))}
                              className="text-neutral-500 hover:text-white transition-colors"
                              title="Copy code"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            </button>
                          </div>
                          <SyntaxHighlighter
                            {...rest}
                            PreTag="div"
                            children={String(children).replace(/\n$/, '')}
                            language={match[1]}
                            style={vscDarkPlus}
                            customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.85rem' }}
                          />
                        </div>
                      ) : (
                        <code {...rest} className="rounded bg-aasila-surface-user px-1.5 py-0.5 text-sm font-mono text-brand-accent">
                          {children}
                        </code>
                      )
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 py-2">
                <div className="h-2 w-2 animate-bounce rounded-full bg-brand-accent/60" style={{ animationDelay: '0ms' }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-brand-accent/60" style={{ animationDelay: '150ms' }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-brand-accent/60" style={{ animationDelay: '300ms' }} />
              </div>
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
                  onClick={() => { if (onFeedback) void onFeedback(message.id, 'positive') }}
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
                  onClick={() => { if (onFeedback) void onFeedback(message.id, 'negative') }}
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
