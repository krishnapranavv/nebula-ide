import { useState } from 'react'
import { useIDEStore } from '@store/ideStore'

type Tab = 'stdout' | 'stderr' | 'info'

export default function OutputPanel() {
  const { executionResult, executionError, isExecuting, outputPanel, toggleOutputPanel } = useIDEStore()
  const [tab, setTab] = useState<Tab>('stdout')

  const hasOutput = !!executionResult || !!executionError || isExecuting

  return (
    <div
      className={`flex-shrink-0 flex flex-col border-t border-ide-border bg-ide-bg transition-all duration-200 ${
        outputPanel === 'open' ? 'h-48' : 'h-8'
      }`}
    >
      {/* Panel header */}
      <div className="flex items-center h-8 px-3 bg-ide-surface border-b border-ide-border gap-3 flex-shrink-0">
        <button
          onClick={toggleOutputPanel}
          className="text-ide-muted hover:text-ide-text text-xs transition-colors mr-1"
        >
          {outputPanel === 'open' ? '▼' : '▲'}
        </button>
        <span className="text-2xs font-semibold uppercase tracking-wider text-ide-muted">Output</span>

        {outputPanel === 'open' && (
          <>
            {(['stdout', 'stderr', 'info'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`text-2xs px-2 py-0.5 rounded transition-colors ${
                  tab === t
                    ? 'bg-ide-elevated text-ide-text border border-ide-border'
                    : 'text-ide-muted hover:text-ide-text'
                }`}
              >
                {t}
                {t === 'stderr' && executionResult?.stderr && (
                  <span className="ml-1 w-1.5 h-1.5 rounded-full bg-ide-red inline-block" />
                )}
              </button>
            ))}
          </>
        )}

        {/* Runtime badge */}
        {executionResult && outputPanel === 'open' && (
          <div className="ml-auto flex items-center gap-2">
            <span className={`text-2xs font-mono px-2 py-0.5 rounded ${
              executionResult.exit_code === 0
                ? 'bg-ide-green-dim text-ide-green border border-ide-green/30'
                : 'bg-ide-red-dim text-ide-red border border-ide-red/30'
            }`}>
              exit {executionResult.exit_code}
            </span>
            <span className="text-2xs text-ide-dim font-mono">{executionResult.runtime_ms}ms</span>
            {executionResult.timed_out && (
              <span className="text-2xs text-ide-amber font-mono">TIMEOUT</span>
            )}
          </div>
        )}
      </div>

      {/* Panel body */}
      {outputPanel === 'open' && (
        <div className="flex-1 overflow-auto p-3 font-mono text-xs">
          {isExecuting && (
            <div className="flex items-center gap-2 text-ide-muted">
              <span className="w-3 h-3 border-2 border-ide-green border-t-transparent rounded-full animate-spin" />
              Running...
            </div>
          )}

          {executionError && !isExecuting && (
            <div className="text-ide-red">
              <span className="text-ide-muted">Error: </span>{executionError}
            </div>
          )}

          {executionResult && !isExecuting && (
            <>
              {tab === 'stdout' && (
                <pre className="text-ide-text whitespace-pre-wrap break-words leading-relaxed">
                  {executionResult.stdout || <span className="text-ide-dim italic">(no output)</span>}
                </pre>
              )}
              {tab === 'stderr' && (
                <pre className={`whitespace-pre-wrap break-words leading-relaxed ${
                  executionResult.stderr ? 'text-ide-red' : 'text-ide-dim italic'
                }`}>
                  {executionResult.stderr || '(no errors)'}
                </pre>
              )}
              {tab === 'info' && (
                <div className="space-y-1 text-ide-muted">
                  <p><span className="text-ide-dim">Language  </span>{executionResult.language}</p>
                  <p><span className="text-ide-dim">Exit code </span><span className={executionResult.exit_code === 0 ? 'text-ide-green' : 'text-ide-red'}>{executionResult.exit_code}</span></p>
                  <p><span className="text-ide-dim">Runtime   </span>{executionResult.runtime_ms}ms</p>
                  <p><span className="text-ide-dim">Timed out </span>{String(executionResult.timed_out)}</p>
                  <p><span className="text-ide-dim">Exec ID   </span><span className="font-mono text-2xs">{executionResult.exec_id}</span></p>
                  <p><span className="text-ide-dim">Timestamp </span>{new Date(executionResult.executed_at).toLocaleString()}</p>
                </div>
              )}
            </>
          )}

          {!hasOutput && (
            <span className="text-ide-dim italic">Run code to see output here</span>
          )}
        </div>
      )}
    </div>
  )
}