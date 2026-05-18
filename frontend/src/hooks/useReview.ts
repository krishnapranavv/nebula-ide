import { useCallback } from 'react'
import { reviewApi } from '@utils/api'
import { useIDEStore } from '@store/ideStore'

export function useReview() {
  const {
    editorContent, language, currentProject, activeTab,
    setReviewing, setReviewResult, setReviewError,
    setReviewPanel, isReviewing,
  } = useIDEStore()

  const review = useCallback(async () => {
    if (isReviewing || !editorContent.trim()) return
    setReviewing(true)
    setReviewError(null)
    setReviewPanel('open')

    try {
      const { data } = await reviewApi.review(
        editorContent,
        language,
        currentProject?.project_id,
        activeTab?.fileId,
      )
      setReviewResult(data)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = e.response?.data?.detail ?? e.message ?? 'Review failed'
      setReviewError(msg)
    } finally {
      setReviewing(false)
    }
  }, [editorContent, language, currentProject, activeTab, isReviewing,
      setReviewing, setReviewResult, setReviewError, setReviewPanel])

  return { review, isReviewing }
}