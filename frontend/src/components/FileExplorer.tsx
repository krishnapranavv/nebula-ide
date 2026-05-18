import { useState } from 'react'
import { useIDEStore } from '@store/ideStore'
import { filesApi, type ProjectFile } from '@utils/api'

const LANG_ICONS: Record<string, string> = {
  py: '🐍', js: '⚡', ts: '⚡', tsx: '⚛', jsx: '⚛',
  cpp: '⚙', c: '⚙', h: '⚙', hpp: '⚙',
  json: '{}', md: '📄', txt: '📄', css: '🎨', html: '🌐',
}

function fileIcon(filename: string) {
  const ext = filename.split('.').pop() ?? ''
  return LANG_ICONS[ext] ?? '📄'
}

interface NewFileFormProps {
  projectId: string
  onCreated: (file: ProjectFile, content: string) => void
  onCancel: () => void
}

function NewFileForm({ projectId, onCreated, onCancel }: NewFileFormProps) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const submit = async () => {
    if (!name.trim()) return
    try {
      const { data } = await filesApi.create(projectId, name.trim(), '')
      onCreated(data, '')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail ?? 'Failed to create file')
    }
  }

  return (
    <div className="px-3 py-2 bg-ide-elevated border-b border-ide-border">
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') submit(); if (e.key === 'Escape') onCancel() }}
        placeholder="filename.py"
        className="w-full bg-ide-bg border border-ide-border text-ide-text text-xs font-mono px-2 py-1 rounded outline-none focus:border-ide-blue"
      />
      {error && <p className="text-ide-red text-2xs mt-1">{error}</p>}
    </div>
  )
}

export default function FileExplorer() {
  const { currentProject, files, setFiles, activeTab, openTab } = useIDEStore()
  const [showNew, setShowNew] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  if (!currentProject) return null

  const handleOpenFile = async (file: ProjectFile) => {
    if (activeTab?.fileId === file.file_id) return
    try {
      const { data } = await filesApi.getContent(currentProject.project_id, file.file_id)
      openTab(file, data.content)
    } catch {
      openTab(file, '')
    }
  }

  const handleDelete = async (file: ProjectFile) => {
    if (!confirm(`Delete "${file.filename}"?`)) return
    setDeleting(file.file_id)
    try {
      await filesApi.delete(currentProject.project_id, file.file_id)
      setFiles(files.filter((f) => f.file_id !== file.file_id))
    } catch {
      // ignore
    } finally {
      setDeleting(null)
    }
  }

  const handleCreated = (file: ProjectFile, content: string) => {
    setFiles([...files, file])
    openTab(file, content)
    setShowNew(false)
  }

  return (
    <aside className="ide-sidebar bg-ide-surface border-r border-ide-border flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-ide-border">
        <span className="text-2xs font-semibold uppercase tracking-wider text-ide-muted">
          Explorer
        </span>
        <button
          onClick={() => setShowNew(true)}
          className="text-ide-muted hover:text-ide-text transition-colors text-sm leading-none"
          title="New file"
        >
          +
        </button>
      </div>

      {/* Project name */}
      <div className="px-3 py-1.5 border-b border-ide-border">
        <span className="text-xs font-semibold text-ide-text truncate block">{currentProject.name}</span>
        <span className="text-2xs text-ide-dim font-mono">{currentProject.language}</span>
      </div>

      {/* New file form */}
      {showNew && (
        <NewFileForm
          projectId={currentProject.project_id}
          onCreated={handleCreated}
          onCancel={() => setShowNew(false)}
        />
      )}

      {/* File list */}
      <nav className="flex-1 overflow-y-auto py-1">
        {files.length === 0 ? (
          <div className="px-3 py-4 text-center">
            <p className="text-ide-dim text-xs">No files yet</p>
            <button onClick={() => setShowNew(true)} className="text-ide-blue text-xs hover:underline mt-1">
              Create a file
            </button>
          </div>
        ) : (
          files.map((file) => (
            <div
              key={file.file_id}
              className={`group flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-ide-elevated transition-colors ${
                activeTab?.fileId === file.file_id ? 'bg-ide-elevated text-ide-text' : 'text-ide-muted'
              }`}
              onClick={() => handleOpenFile(file)}
            >
              <span className="text-sm flex-shrink-0">{fileIcon(file.filename)}</span>
              <span className="text-xs font-mono flex-1 truncate">{file.filename}</span>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(file) }}
                className="opacity-0 group-hover:opacity-100 text-ide-dim hover:text-ide-red transition-all text-xs"
                disabled={deleting === file.file_id}
              >
                {deleting === file.file_id ? '…' : '×'}
              </button>
            </div>
          ))
        )}
      </nav>
    </aside>
  )
}