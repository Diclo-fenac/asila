import { useState, useRef } from 'react'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { useUploadDocument } from '../../hooks/useDocuments'
import { Upload, X } from 'lucide-react'

interface DocumentUploadModalProps {
  isOpen: boolean
  onClose: () => void
}

export function DocumentUploadModal({ isOpen, onClose }: DocumentUploadModalProps) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadMutation = useUploadDocument()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      if (!title) {
        setTitle(e.target.files[0].name.split('.')[0])
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !title) return

    uploadMutation.mutate(
      { file, title },
      {
        onSuccess: () => {
          setTitle('')
          setFile(null)
          onClose()
        },
      }
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Upload Document">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Input label="Document Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Employee Handbook"
            required
            disabled={uploadMutation.isPending}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-aasila-text">File</label>
          {file ? (
            <div className="flex items-center justify-between rounded-md border border-brand-accent/30 bg-brand-accent/5 p-3">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-brand-accent/20 text-brand-accent">
                  <Upload className="h-4 w-4" />
                </div>
                <div className="truncate">
                  <p className="truncate text-sm font-medium text-aasila-text">{file.name}</p>
                  <p className="text-xs text-aasila-muted">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="p-2 text-aasila-muted hover:text-red-500 transition-colors"
                disabled={uploadMutation.isPending}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed border-aasila-border/60 bg-aasila-surface p-8 text-center transition-colors hover:border-brand-accent/50 hover:bg-aasila-surface-low"
            >
              <Upload className="mb-2 h-8 w-8 text-aasila-muted" />
              <p className="text-sm font-medium text-aasila-text">Click to upload or drag and drop</p>
              <p className="mt-1 text-xs text-aasila-muted">PDF, DOCX, TXT up to 50MB</p>
            </div>
          )}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            disabled={uploadMutation.isPending}
          />
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose} disabled={uploadMutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={!file || !title || uploadMutation.isPending}>
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
