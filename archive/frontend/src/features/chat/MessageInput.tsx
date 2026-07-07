import {
  useRef,
  useEffect,
  forwardRef,
  useState,
  type TextareaHTMLAttributes,
} from 'react'
import { cn } from '../../utils/cn'

interface MessageInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  onSend: (content: string) => void
  isLoading?: boolean
}

export const MessageInput = forwardRef<HTMLTextAreaElement, MessageInputProps>(
  ({ onSend, isLoading, className, disabled, ...props }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement | null>(null)

    const [text, setText] = useState('')

    // Auto-resize
    useEffect(() => {
      const el = textareaRef.current
      if (!el) return

      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`
    })

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        const content = text.trim()
        if (content && !isLoading) {
          onSend(content)
          setText('')
          if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
          }
        }
      }
    }

    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 relative">
        <div className="relative flex items-end rounded-2xl apple-glass-input border border-aasila-border transition-all duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] focus-within:border-brand-accent/50 p-3">
          {/* Left Functional Icons */}
          <div className="flex mb-1 items-center gap-1 pl-2 text-aasila-muted">
            <button type="button" title="Upload files" className="p-1.5 hover:bg-aasila-surface-user active:bg-aasila-border rounded-full transition-colors" disabled={isLoading}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm3.65 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75z" />
              </svg>
            </button>
            <button type="button" title="Web Search" className="p-1.5 hover:bg-aasila-surface-user active:bg-aasila-border rounded-full transition-colors" disabled={isLoading}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
              </svg>
            </button>
            <div className="h-5 w-[1px] bg-aasila-border mx-0.5" />
            <button type="button" title="Reasoning Mode" className="p-1.5 hover:bg-aasila-surface-user active:bg-aasila-border rounded-full transition-colors" disabled={isLoading}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L4.2 15.3m15.6 0v1.47a2.25 2.25 0 01-1.13 1.954l-5.36 3.1a2.25 2.25 0 01-2.34 0l-5.36-3.1a2.25 2.25 0 01-1.13-1.954V15.3c0-1.42 1.138-2.617 2.582-2.923l1.23-.263a11.208 11.208 0 014.376 0l1.23.263c1.444.306 2.582 1.503 2.582 2.923v1.47z" />
              </svg>
            </button>
            <div className="h-5 w-[1px] bg-[var(--color-neutral-200)] mx-0.5" />
            <button type="button" title="Workspace Context" className="p-1.5 hover:bg-[var(--color-neutral-100)] active:bg-[var(--color-neutral-200)] rounded-full transition-colors" disabled={isLoading}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </button>
          </div>

          <textarea
            id="chat-input"
            ref={(node) => {
              textareaRef.current = node
              if (typeof ref === 'function') ref(node)
              else if (ref) ref.current = node
            }}
            className={cn(
              'flex-1 max-h-[300px] min-h-[50px] w-full bg-transparent py-3 px-3 text-[16px] leading-relaxed placeholder:text-aasila-muted/70 text-aasila-text border-transparent focus:border-transparent focus:ring-0 focus:ring-offset-0 resize-none overflow-hidden font-medium',
              className,
            )}
            placeholder="Ask about lease clauses, compliance, or tenant obligations..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            rows={1}
            {...props}
          />

          {/* Right Action Button (Send / Mic) */}
          <div className="pr-1 mb-1">
            <button
              type="button"
              onClick={() => {
                const content = text.trim()
                if (content && !isLoading) {
                  onSend(content)
                  setText('')
                  if (textareaRef.current) {
                    textareaRef.current.style.height = 'auto'
                  }
                }
              }}
              disabled={isLoading || disabled || !text.trim()}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-accent text-white hover:bg-brand-accent-hover btn-skeuo disabled:opacity-40 disabled:hover:bg-brand-accent disabled:transform-none disabled:box-shadow-none"
              aria-label="Send message"
            >
              {isLoading ? (
                <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
                </svg>
              )}
            </button>
          </div>
        </div>
        <div className="flex justify-center items-center px-4 mt-1">
          <p className="text-[11px] font-medium text-aasila-muted opacity-70">
            <kbd className="font-mono bg-aasila-surface-user px-1.5 py-0.5 rounded border border-aasila-border mr-1">Shift</kbd> + <kbd className="font-mono bg-aasila-surface-user px-1.5 py-0.5 rounded border border-aasila-border mr-1">Enter</kbd> to add a new line
          </p>
        </div>
      </div>
    )
  },
)

MessageInput.displayName = 'MessageInput'
