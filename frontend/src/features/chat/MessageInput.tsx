import {
  useRef,
  useEffect,
  forwardRef,
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
        const content = textareaRef.current?.value.trim()
        if (content && !isLoading) {
          onSend(content)
          if (textareaRef.current) {
            textareaRef.current.value = ''
            textareaRef.current.style.height = 'auto'
          }
        }
      }
    }

    return (
      <div className="flex w-full flex-col gap-2">
        <div className="relative flex items-end rounded-sm border border-aasila-border bg-aasila-surface-ai shadow-sm transition-all focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500">
          <textarea
            ref={(node) => {
              textareaRef.current = node
              if (typeof ref === 'function') ref(node)
              else if (ref) ref.current = node
            }}
            className={cn(
              'max-h-[200px] min-h-[56px] w-full rounded-sm bg-transparent py-4 pl-4 pr-12 text-[15px] leading-normal placeholder:text-aasila-muted text-aasila-text outline-none transition-all resize-none',
              className,
            )}
            placeholder="Message Aasila..."
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            rows={1}
            {...props}
          />
          <button
            type="button"
            onClick={() => {
              const el = textareaRef.current
              if (!el) return
              const content = el.value.trim()
              if (content && !isLoading) {
                onSend(content)
                el.value = ''
                el.style.height = 'auto'
              }
            }}
            disabled={isLoading || disabled}
            className="absolute right-2 bottom-2 flex h-8 w-8 items-center justify-center rounded-sm bg-emerald-500 text-white transition-colors hover:bg-emerald-600 disabled:opacity-50"
            aria-label="Send message"
          >
            {isLoading ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-center text-xs font-medium text-aasila-muted">
          Press Enter to send, Shift + Enter for new line.
        </p>
      </div>
    )
  },
)

MessageInput.displayName = 'MessageInput'
