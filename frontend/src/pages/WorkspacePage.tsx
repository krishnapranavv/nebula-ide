import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { projectsApi, filesApi } from '@utils/api'
import { useIDEStore } from '@store/ideStore'
import TopBar from '@components/TopBar'
import FileExplorer from '@components/FileExplorer'
import EditorArea from '@components/EditorArea'
import OutputPanel from '@components/OutputPanel'
import ReviewPanel from '@components/ReviewPanel'
import { useAutoSave } from '@hooks/useAutoSave'

export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { currentProject, setProject, setFiles, files } = useIDEStore()
  useAutoSave()  // Mount autosave hook at workspace level

  useEffect(() => {
    if (!projectId) { navigate('/dashboard'); return }

    // Hydrate project if we arrived via direct URL (not from dashboard)
    if (!currentProject || currentProject.project_id !== projectId) {
      projectsApi.get(projectId)
        .then(async ({ data: project }) => {
          setProject(project)
          const { data } = await filesApi.list(projectId)
          setFiles(data.files)
        })
        .catch(() => navigate('/dashboard'))
    }
  }, [projectId])  // eslint-disable-line react-hooks/exhaustive-deps

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-screen bg-ide-bg gap-3 text-ide-muted">
        <span className="w-5 h-5 border-2 border-ide-blue border-t-transparent rounded-full animate-spin" />
        Loading workspace…
      </div>
    )
  }

  return (
    <div className="ide-layout">
      {/* Top bar — spans full width */}
      <TopBar />

      {/* Left sidebar — file explorer */}
      <FileExplorer />

      {/* Main area — editor + output stacked */}
      <main className="ide-main overflow-hidden">
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Editor */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <EditorArea />
            <OutputPanel />
          </div>

          {/* Review panel — slides in from right */}
          <ReviewPanel />
        </div>
      </main>
    </div>
  )
}