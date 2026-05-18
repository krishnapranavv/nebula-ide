import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectsApi, filesApi, type Project, type Language } from '@utils/api'
import { useAuthStore } from '@store/authStore'
import { useIDEStore } from '@store/ideStore'

const LANG_META: Record<Language, { icon: string; color: string; bg: string }> = {
  python:     { icon: '🐍', color: 'text-ide-amber',  bg: 'bg-ide-amber-dim border-ide-amber/30' },
  javascript: { icon: '⚡', color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-500/30' },
  cpp:        { icon: '⚙', color: 'text-ide-blue',   bg: 'bg-ide-blue-dim border-ide-blue/30' },
}

const LANG_OPTIONS: { value: Language; label: string }[] = [
  { value: 'python',     label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'cpp',        label: 'C++' },
]

function CreateModal({ onClose, onCreate }: { onClose: () => void; onCreate: (p: Project) => void }) {
  const [name, setName] = useState('')
  const [lang, setLang] = useState<Language>('python')
  const [desc, setDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError('')
    try {
      const { data } = await projectsApi.create(name.trim(), lang, desc.trim())
      // Create a starter file
      await filesApi.create(data.project_id, `main.${lang === 'python' ? 'py' : lang === 'javascript' ? 'js' : 'cpp'}`, '')
      onCreate(data)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail ?? 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-ide-surface border border-ide-border rounded-xl p-6 w-full max-w-md shadow-2xl slide-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-ide-text">New project</h2>
          <button onClick={onClose} className="text-ide-dim hover:text-ide-text text-xl">×</button>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-ide-muted block mb-1.5">Project name</label>
            <input
              autoFocus value={name} onChange={(e) => setName(e.target.value)} required
              placeholder="my-awesome-project"
              className="w-full bg-ide-elevated border border-ide-border text-ide-text text-sm px-3 py-2 rounded-lg outline-none focus:border-ide-blue"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-ide-muted block mb-1.5">Language</label>
            <div className="flex gap-2">
              {LANG_OPTIONS.map((opt) => (
                <button key={opt.value} type="button" onClick={() => setLang(opt.value)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border text-sm transition-all ${
                    lang === opt.value
                      ? `${LANG_META[opt.value].bg} ${LANG_META[opt.value].color} border-current`
                      : 'bg-ide-elevated border-ide-border text-ide-muted hover:text-ide-text'
                  }`}>
                  <span>{LANG_META[opt.value].icon}</span>
                  <span className="text-xs">{opt.label}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-ide-muted block mb-1.5">Description <span className="text-ide-dim">(optional)</span></label>
            <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="What does this project do?"
              className="w-full bg-ide-elevated border border-ide-border text-ide-text text-sm px-3 py-2 rounded-lg outline-none focus:border-ide-blue"
            />
          </div>
          {error && <div className="text-xs text-ide-red bg-ide-red-dim border border-ide-red/30 px-3 py-2 rounded-lg">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 bg-ide-blue hover:bg-ide-blue/90 disabled:opacity-50 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2">
            {loading ? <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Creating…</> : 'Create project'}
          </button>
        </form>
      </div>
    </div>
  )
}

function ProjectCard({ project, onOpen, onDelete }: { project: Project; onOpen: () => void; onDelete: () => void }) {
  const meta = LANG_META[project.language] ?? LANG_META.python
  const updated = new Date(project.updated_at).toLocaleDateString()
  return (
    <div className="group bg-ide-surface border border-ide-border rounded-xl p-5 hover:border-ide-blue/50 transition-all cursor-pointer" onClick={onOpen}>
      <div className="flex items-start justify-between mb-3">
        <span className={`text-xs font-mono px-2 py-0.5 rounded border ${meta.bg} ${meta.color}`}>
          {meta.icon} {project.language}
        </span>
        <button onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="opacity-0 group-hover:opacity-100 text-ide-dim hover:text-ide-red text-sm transition-all">×</button>
      </div>
      <h3 className="text-sm font-semibold text-ide-text mb-1 truncate">{project.name}</h3>
      {project.description && <p className="text-xs text-ide-muted truncate mb-3">{project.description}</p>}
      <p className="text-2xs text-ide-dim mt-auto">Updated {updated}</p>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  const { setProject, setFiles, resetWorkspace } = useIDEStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    resetWorkspace()
    projectsApi.list().then(({ data }) => setProjects(data.projects)).finally(() => setLoading(false))
  }, [resetWorkspace])

  const openProject = async (project: Project) => {
    setProject(project)
    const { data } = await filesApi.list(project.project_id)
    setFiles(data.files)
    navigate(`/workspace/${project.project_id}`)
  }

  const deleteProject = async (project: Project) => {
    if (!confirm(`Delete "${project.name}"? This cannot be undone.`)) return
    await projectsApi.delete(project.project_id)
    setProjects((ps) => ps.filter((p) => p.project_id !== project.project_id))
  }

  return (
    <div className="min-h-screen bg-ide-bg flex flex-col">
      {/* Header */}
      <header className="bg-ide-surface border-b border-ide-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🌌</span>
          <span className="text-sm font-bold text-ide-text">Nebula IDE</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-ide-muted">Hi, <span className="text-ide-text font-medium">{user?.username}</span></span>
          <button onClick={() => { clearAuth(); navigate('/login') }} className="text-xs text-ide-dim hover:text-ide-red transition-colors">
            Sign out
          </button>
        </div>
      </header>

      {/* Body */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-ide-text">Projects</h2>
            <p className="text-xs text-ide-muted mt-0.5">{projects.length} project{projects.length !== 1 ? 's' : ''}</p>
          </div>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-ide-blue hover:bg-ide-blue/90 text-white text-sm font-medium rounded-lg transition-all">
            + New project
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48 gap-3 text-ide-muted">
            <span className="w-5 h-5 border-2 border-ide-blue border-t-transparent rounded-full animate-spin" />
            Loading projects…
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <span className="text-5xl mb-4">📂</span>
            <p className="text-sm font-medium text-ide-muted">No projects yet</p>
            <p className="text-xs text-ide-dim mt-1 mb-4">Create your first project to start coding</p>
            <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-ide-blue text-white text-sm font-medium rounded-lg hover:bg-ide-blue/90">
              Create project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <ProjectCard key={p.project_id} project={p} onOpen={() => openProject(p)} onDelete={() => deleteProject(p)} />
            ))}
          </div>
        )}
      </main>

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreate={(p) => { setProjects((ps) => [p, ...ps]); setShowCreate(false); openProject(p) }}
        />
      )}
    </div>
  )
}