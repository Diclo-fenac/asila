import { type ReactNode } from 'react'
import { cn } from '../../utils/cn'

interface MobileSidebarProps {
  isOpen: boolean
  onClose: () => void
  children: ReactNode
}

export function MobileSidebar({ isOpen, onClose, children }: MobileSidebarProps) {
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-[260px] transform transition-transform duration-300 ease-in-out lg:hidden',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-full flex-col border-r border-aasila-border bg-aasila-bg-sidebar">
          {/* Close button */}
          <div className="flex items-center justify-between p-4">
            <h1 className="text-base font-semibold text-aasila-text">Aasila</h1>
            <button
              type="button"
              onClick={onClose}
              className="rounded-sm p-1 text-aasila-muted transition-colors hover:bg-aasila-border/30 hover:text-aasila-text"
              aria-label="Close navigation"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}
