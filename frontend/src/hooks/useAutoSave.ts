import { useEffect, useRef, useCallback } from 'react'
import { filesApi } from '@utils/api'
import { useIDEStore } from '@store/ideStore'

const AUTOSAVE_DELAY_MS = 2000

export function useAutoSave() {
  const { activeTab, currentProject, markTabClean } = useIDEStore()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isSavingRef = useRef(false)

  const save = useCallback(async (projectId: string, fileId: string, content: string) => {
    if (isSavingRef.current) return
    isSavingRef.current = true
    try {
      await filesApi.save(projectId, fileId, content)
      markTabClean(fileId)
    } catch (err) {
      console.warn('Auto-save failed:', err)
    } finally {
      isSavingRef.current = false
    }
  }, [markTabClean])

  useEffect(() => {
    if (!activeTab?.isDirty || !currentProject) return

    if (timerRef.current) clearTimeout(timerRef.current)

    timerRef.current = setTimeout(() => {
      save(currentProject.project_id, activeTab.fileId, activeTab.content)
    }, AUTOSAVE_DELAY_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [activeTab?.content, activeTab?.isDirty, activeTab?.fileId, currentProject, save])

  // Force-save immediately (e.g. before execution or closing tab)
  const saveNow = useCallback(async () => {
    if (!activeTab || !currentProject) return
    if (timerRef.current) clearTimeout(timerRef.current)
    await save(currentProject.project_id, activeTab.fileId, activeTab.content)
  }, [activeTab, currentProject, save])

  return { saveNow, isSaving: isSavingRef.current }
}