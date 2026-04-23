import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Document } from '../types/document'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

// Placeholder — wire to real API when /documents endpoint exists
async function fetchDocuments(): Promise<Document[]> {
  // Stub: replace with apiClient.get('/documents') when available
  return []
}

const fileIcons: Record<string, string> = {
  pdf: 'article',
  docx: 'description',
}

function getFileType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? ''
  return fileIcons[ext] ?? 'description'
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

const statusConfig: Record<string, { label: string; color: string; bg: string; border: string }> = {
  ready: { label: 'Ready', color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  processing: { label: 'Processing', color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  failed: { label: 'Failed', color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  pending: { label: 'Pending', color: 'text-slate-500', bg: 'bg-slate-500/10', border: 'border-slate-500/30' },
}

export function DocumentKnowledgeBase() {
  const [activeTab, setActiveTab] = useState<'all' | 'archived' | 'trash'>('all')
  const { data: documents, isLoading, isError } = useQuery<Document[], Error>({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
  })

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-8">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 sm:mb-10 sm:flex-row sm:items-end sm:justify-between border-b border-aasila-border/50 pb-6">
        <div>
          <h2 className="mb-2 text-[12px] font-bold uppercase tracking-[0.2em] text-emerald-500">Internal Management</h2>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-aasila-text">Document Knowledge Base</h1>
          <p className="mt-2 max-w-lg text-[15px] text-aasila-muted">
            Manage access levels, security clearance, and audit authentication vectors for all tenant administrators.
          </p>
        </div>
        <button
          type="button"
          className="flex shrink-0 items-center gap-2 rounded-sm bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-600"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          + Upload Document
        </button>
      </div>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4 sm:gap-6 sm:mb-12">
        {[
          { label: 'Total Documents', value: '1,284', delta: '+12.5%' },
          { label: 'Storage Used', value: '42.8 GB', delta: 'of 100 GB' },
          { label: 'Active Indices', value: '24', delta: 'Healthy' },
          { label: 'Failed Ingestions', value: '3', delta: 'Action Required' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-sm border border-aasila-border/50 bg-aasila-surface-user p-4 sm:p-6">
            <p className="mb-3 text-[11px] font-bold uppercase tracking-widest text-aasila-muted">{stat.label}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-bold text-aasila-text">{isLoading ? '—' : stat.value}</span>
              <span className={`text-xs font-mono ${stat.delta.includes('Required') ? 'text-red-500' : 'text-emerald-500'}`}>
                {stat.delta}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-sm border border-aasila-border/50 bg-aasila-surface-ai">
        <div className="flex items-center justify-between border-b border-aasila-border/50 bg-aasila-surface-user px-4 py-4 sm:px-6">
          <div className="flex gap-4">
            {(['all', 'archived', 'trash'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`pb-1 text-xs font-bold uppercase tracking-widest transition-colors ${
                  activeTab === tab
                    ? 'border-b-2 border-emerald-500 text-emerald-500'
                    : 'text-aasila-muted hover:text-aasila-text'
                }`}
                aria-selected={activeTab === tab}
                role="tab"
              >
                {tab === 'all' ? 'All Files' : tab === 'archived' ? 'Archived' : 'Trash'}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="rounded p-1 transition-colors hover:bg-aasila-bg-main"
            aria-label="Filter documents"
          >
            <svg className="h-5 w-5 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-red-500">Unable to load documents.</p>
          </div>
        ) : !documents || documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <svg className="mb-3 h-8 w-8 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm font-medium text-aasila-text">No documents yet</p>
            <p className="text-xs text-aasila-muted">Upload your first document to get started.</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-aasila-border/50 bg-aasila-bg-sidebar/50 text-[11px] font-bold uppercase tracking-widest text-aasila-muted">
                    <th scope="col" className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        Name
                        <svg className="h-[14px] w-[14px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" />
                        </svg>
                      </div>
                    </th>
                    <th scope="col" className="px-6 py-4">Type</th>
                    <th scope="col" className="px-6 py-4">Date Uploaded</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4 w-16" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-aasila-border/30">
                  {documents.map((doc) => {
                    const status = statusConfig[doc.status] ?? statusConfig.pending
                    return (
                      <tr key={doc.id} className="group transition-colors hover:bg-aasila-bg-main">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <svg className="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d={getFileType(doc.filename)} />
                            </svg>
                            <div>
                              <p className="text-sm font-semibold text-aasila-text">{doc.filename}</p>
                              <p className="text-[11px] font-mono text-aasila-muted">UID: {doc.id.slice(0, 8).toUpperCase()}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-aasila-muted">{doc.file_type}</td>
                        <td className="px-6 py-4 text-xs text-aasila-text">{formatDate(doc.uploaded_at)}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${status.color} ${status.bg} ${status.border}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            type="button"
                            className="opacity-0 transition-opacity group-hover:opacity-100 p-1"
                            aria-label={`Actions for ${doc.filename}`}
                          >
                            <svg className="h-5 w-5 text-aasila-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile card layout */}
            <div className="space-y-3 p-4 md:hidden">
              {documents.map((doc) => {
                const status = statusConfig[doc.status] ?? statusConfig.pending
                return (
                  <div key={doc.id} className="rounded-sm border border-aasila-border bg-aasila-surface-user p-4">
                    <div className="mb-2 flex items-center gap-3">
                      <svg className="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={getFileType(doc.filename)} />
                      </svg>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-aasila-text">{doc.filename}</p>
                        <p className="text-[11px] font-mono text-aasila-muted">{doc.file_type} · {formatDate(doc.uploaded_at)}</p>
                      </div>
                    </div>
                    <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${status.color} ${status.bg} ${status.border}`}>
                      {status.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
