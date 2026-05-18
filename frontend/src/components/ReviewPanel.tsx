import { useState } from 'react'
import { useIDEStore } from '@store/ideStore'
import ProviderBadge from './ProviderBadge'
import type { Finding } from '@utils/api'

type SevFilter = 'all' | 'error' | 'warning' | 'info'

function ScoreRing({ score }: { score: number }) {
  const cls = score >= 8 ? 'score-high' : score >= 5 ? 'score-mid' : 'score-low'
  return <div className={`score-ring ${cls}`}>{score}/10</div>
}

function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false)
  const sevClass = `sev-${finding.severity}`

  return (
    <div className="border border-ide-border rounded bg-ide-elevated mb-2 overflow-hidden">
      <button
        className="w-full flex items-start gap-2 p-2.5 text-left hover:bg-ide-bg transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span className={`text-2xs font-mono px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${sevClass}`}>
          {finding.severity}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-ide-text leading-snug">{finding.message}</p>
          <p className="text-2xs text-ide-dim mt-0.5 font-mono">
            line {finding.line} · {finding.rule_id} · {finding.category}
          </p>
        </div>
        <span className="text-ide-dim text-xs flex-shrink-0">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-ide-border animate-fade-in space-y-2">
          <p className="text-xs text-ide-muted leading-relaxed mt-2">{finding.explanation}</p>
          {finding.fix && (
            <div className="mt-2">
              <p className="text-2xs font-semibold text-ide-green uppercase tracking-wider mb-1">Suggested fix</p>
              <pre className="bg-ide-bg text-ide-text text-xs font-mono p-2 rounded border border-ide-border overflow-x-auto leading-relaxed whitespace-pre-wrap break-words">
                {finding.fix}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ReviewPanel() {
  const { reviewResult, reviewError, isReviewing, reviewPanel, toggleReviewPanel } = useIDEStore()
  const [filter, setFilter] = useState<SevFilter>('all')

  const filtered = reviewResult?.findings.filter(
    (f) => filter === 'all' || f.severity === filter
  ) ?? []

  const counts = reviewResult
    ? {
        error:   reviewResult.findings.filter((f) => f.severity === 'error').length,
        warning: reviewResult.findings.filter((f) => f.severity === 'warning').length,
        info:    reviewResult.findings.filter((f) => f.severity === 'info').length,
      }
    : null

  return (
    <div
      className={`flex-shrink-0 flex flex-col border-l border-ide-border bg-ide-surface transition-all duration-200 ${
        reviewPanel === 'open' ? 'w-80' : 'w-0 overflow-hidden'
      }`}
    >
      {reviewPanel === 'open' && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-ide-border flex-shrink-0">
            <span className="text-2xs font-semibold uppercase tracking-wider text-ide-muted">AI Review</span>
            <button onClick={toggleReviewPanel} className="text-ide-dim hover:text-ide-text text-sm">×</button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-3">
            {isReviewing && (
              <div className="flex flex-col items-center justify-center h-40 gap-3">
                <span className="w-8 h-8 border-2 border-ide-purple border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-ide-muted">Analysing code…</p>
              </div>
            )}

            {reviewError && !isReviewing && (
              <div className="rounded bg-ide-red-dim border border-ide-red/30 p-3 text-xs text-ide-red">
                {reviewError}
              </div>
            )}

            {reviewResult && !isReviewing && (
              <div className="fade-in space-y-4">
                {/* Score + summary */}
                <div className="flex items-start gap-3">
                  <ScoreRing score={reviewResult.overall_score} />
                  <div className="flex-1">
                    <p className="text-xs text-ide-text leading-relaxed">{reviewResult.summary}</p>
                    <div className="mt-1.5">
                      <ProviderBadge
                        modelUsed={reviewResult.model_used}
                        tokensUsed={reviewResult.tokens_used}
                      />
                    </div>
                  </div>
                </div>

                {/* Counts */}
                {counts && (
                  <div className="flex gap-2">
                    {(['all', 'error', 'warning', 'info'] as SevFilter[]).map((s) => {
                      const count = s === 'all' ? reviewResult.findings.length : counts[s]
                      return (
                        <button
                          key={s}
                          onClick={() => setFilter(s)}
                          className={`text-2xs px-2 py-0.5 rounded border transition-colors ${
                            filter === s
                              ? 'bg-ide-elevated text-ide-text border-ide-border'
                              : 'text-ide-dim border-transparent hover:border-ide-border'
                          }`}
                        >
                          {s === 'all' ? `All ${count}` : (
                            <span className={`sev-${s} px-1 rounded`}>{count} {s}</span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}

                {/* Findings */}
                {filtered.length === 0 ? (
                  <div className="text-center py-6">
                    <p className="text-2xl">✅</p>
                    <p className="text-xs text-ide-muted mt-2">No {filter === 'all' ? '' : filter} issues found</p>
                  </div>
                ) : (
                  filtered.map((f, i) => <FindingCard key={`${f.rule_id}-${f.line}-${i}`} finding={f} />)
                )}
              </div>
            )}

            {!reviewResult && !isReviewing && !reviewError && (
              <div className="flex flex-col items-center justify-center h-40 text-ide-dim">
                <p className="text-3xl mb-2">✦</p>
                <p className="text-xs">Click Review to analyse your code</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}