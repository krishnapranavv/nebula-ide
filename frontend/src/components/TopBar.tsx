import { useIDEStore } from '@store/ideStore'
import { useAuthStore } from '@store/authStore'
import { useExecution } from '@hooks/useExecution'
import { useReview } from '@hooks/useReview'
import { useAutoSave } from '@hooks/useAutoSave'
import { useNavigate } from 'react-router-dom'
import type { Language } from '@utils/api'

const LANG_CONFIG: Record<Language, { label: string; color: string; ext: string }> = {
  python:     { label: 'Python',     color: 'text-ide-amber',  ext: 'py'  },
  javascript: { label: 'JavaScript', color: 'text-ide-amber',  ext: 'js'  },
  cpp:        { label: 'C++',        color: 'text-ide-blue',   ext: 'cpp' },
}

export default function TopBar() {
  const { currentProject, activeTab, language, isExecuting, isReviewing, reviewPanel, toggleReviewPanel } = useIDEStore()
  const { user, clearAuth } = useAuthStore()
  const { run, isExecuting: running } = useExecution()
  const { review, isReviewing: reviewing } = useReview()
  const { saveNow } = useAutoSave()
  const navigate = useNavigate()

  const langCfg = LANG_CONFIG[language] ?? LANG_CONFIG.python

  const handleRun = async () => {
    await saveNow()
    run()
  }

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <header className="ide-topbar h-10 bg-ide-surface border-b border-ide-border flex items-center px-3 gap-2 select-none z-30">
      {/* Brand */}
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-1.5 text-ide-muted hover:text-ide-text transition-colors mr-1"
      >
        <span className="text-sm">🌌</span>
        <span className="text-xs font-semibold text-ide-text">Nebula</span>
      </button>

      <div className="w-px h-4 bg-ide-border" />

      {/* Tab bar */}
      {activeTab ? (
        <div className="flex items-center gap-0.5 min-w-0">
          <span className="text-xs text-ide-muted font-mono">{activeTab.filename}</span>
          {activeTab.isDirty && (
            <span className="w-1.5 h-1.5 rounded-full bg-ide-amber ml-1 flex-shrink-0" title="Unsaved changes" />
          )}
        </div>
      ) : (
        <span className="text-xs text-ide-dim">{currentProject?.name ?? 'No file open'}</span>
      )}

      {/* Language badge */}
      <span className={`text-2xs font-mono px-1.5 py-0.5 rounded bg-ide-elevated border border-ide-border ${langCfg.color} ml-1 flex-shrink-0`}>
        {langCfg.label}
      </span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={running || !activeTab}
        className="btn-run flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold bg-ide-green-dim text-ide-green border border-ide-green/30 hover:bg-ide-green/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        {running ? (
          <>
            <span className="w-3 h-3 border-2 border-ide-green border-t-transparent rounded-full animate-spin" />
            Running
          </>
        ) : (
          <>▶ Run</>
        )}
      </button>

      {/* Review button */}
      <button
        onClick={reviewing ? undefined : review}
        disabled={reviewing || !activeTab}
        className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold bg-ide-purple-dim text-ide-purple border border-ide-purple/30 hover:bg-ide-purple/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        {reviewing ? (
          <>
            <span className="w-3 h-3 border-2 border-ide-purple border-t-transparent rounded-full animate-spin" />
            Reviewing
          </>
        ) : (
          <>✦ Review</>
        )}
      </button>

      <div className="w-px h-4 bg-ide-border" />

      {/* User menu */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-ide-muted hidden sm:block">{user?.username}</span>
        <button
          onClick={handleLogout}
          className="text-xs text-ide-dim hover:text-ide-red transition-colors px-1 py-0.5 rounded"
          title="Sign out"
        >
          ⎋
        </button>
      </div>
    </header>
  )
}