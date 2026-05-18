import { useCallback } from 'react'
import { executeApi } from '@utils/api'
import { useIDEStore } from '@store/ideStore'

export function useExecution() {
  const {
    editorContent, language, currentProject, activeTab,
    setExecuting, setExecutionResult, setExecutionError,
    setOutputPanel, isExecuting,
  } = useIDEStore()

  const run = useCallback(async (stdin = '') => {
    if (isExecuting || !editorContent.trim()) return
    setExecuting(true)
    setExecutionError(null)
    setOutputPanel('open')

    try {
      const { data } = await executeApi.run(
        editorContent,
        language,
        stdin,
        currentProject?.project_id,
        activeTab?.fileId,
      )
      setExecutionResult(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Execution failed'
      setExecutionError(msg)
    } finally {
      setExecuting(false)
    }
  }, [editorContent, language, currentProject, activeTab, isExecuting,
      setExecuting, setExecutionResult, setExecutionError, setOutputPanel])

  return { run, isExecuting }
}