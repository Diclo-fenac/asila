import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: string
  message: string
  type: ToastType
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (message: string, type?: ToastType) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = `toast-${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id, message, type }])
    // Auto-dismiss after 4s
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return { addToast: ctx.addToast }
}

const typeConfig: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: { bg: 'bg-emerald-50 dark:bg-emerald-500/10', border: 'border-emerald-500/30', icon: 'text-emerald-500' },
  error: { bg: 'bg-red-50 dark:bg-red-500/10', border: 'border-red-500/30', icon: 'text-red-500' },
  warning: { bg: 'bg-amber-50 dark:bg-amber-500/10', border: 'border-amber-500/30', icon: 'text-amber-500' },
  info: { bg: 'bg-blue-50 dark:bg-blue-500/10', border: 'border-blue-500/30', icon: 'text-blue-500' },
}

function ToastContainer() {
  const ctx = useContext(ToastContext)
  if (!ctx || ctx.toasts.length === 0) return null

  return (
    <div className="fixed right-4 top-20 z-[200] flex flex-col gap-2" aria-live="polite">
      {ctx.toasts.map((toast) => {
        const config = typeConfig[toast.type]
        return (
          <div
            key={toast.id}
            className={`flex items-center gap-3 rounded-md border px-4 py-3 text-sm shadow-lg ${config.bg} ${config.border}`}
            role="status"
          >
            {toast.type === 'success' && (
              <svg className={`h-4 w-4 shrink-0 ${config.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
            {toast.type === 'error' && (
              <svg className={`h-4 w-4 shrink-0 ${config.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            {toast.type === 'warning' && (
              <svg className={`h-4 w-4 shrink-0 ${config.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            {toast.type === 'info' && (
              <svg className={`h-4 w-4 shrink-0 ${config.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            <span className="text-aasila-text">{toast.message}</span>
            <button
              type="button"
              onClick={() => ctx.removeToast(toast.id)}
              className="ml-2 shrink-0 text-aasila-muted hover:text-aasila-text"
              aria-label="Dismiss notification"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )
      })}
    </div>
  )
}
