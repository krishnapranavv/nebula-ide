import Editor from '@monaco-editor/react'
import { useIDEStore } from '@store/ideStore'
import type { Language } from '@utils/api'

const MONACO_LANG: Record<Language, string> = {
  python: 'python',
  javascript: 'javascript',
  cpp: 'cpp',
}

const STARTER_CODE: Record<Language, string> = {
  python: '# Welcome to Nebula IDE\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
  javascript: '// Welcome to Nebula IDE\n\nfunction main() {\n  console.log("Hello, World!");\n}\n\nmain();\n',
  cpp: '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}\n',
}

export default function EditorArea() {
  const {
    editorContent, setEditorContent, language,
    openTabs, activeTab, closeTab, setActiveTab,
  } = useIDEStore()

  const displayContent = 
    (activeTab?.content ?? editorContent) || STARTER_CODE[language]

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-ide-bg">
      {/* Tab bar */}
      {openTabs.length > 0 && (
        <div className="flex items-end bg-ide-surface border-b border-ide-border overflow-x-auto flex-shrink-0">
          {openTabs.map((tab) => (
            <div
              key={tab.fileId}
              className={`flex items-center gap-2 px-4 py-2 cursor-pointer text-xs font-mono border-r border-ide-border flex-shrink-0 transition-colors ${
                tab.fileId === activeTab?.fileId
                  ? 'tab-active'
                  : 'text-ide-muted hover:text-ide-text hover:bg-ide-elevated'
              }`}
              onClick={() => setActiveTab(tab.fileId)}
            >
              <span>{tab.filename}</span>
              {tab.isDirty && <span className="w-1.5 h-1.5 rounded-full bg-ide-amber flex-shrink-0" />}
              <button
                onClick={(e) => { e.stopPropagation(); closeTab(tab.fileId) }}
                className="opacity-60 hover:opacity-100 hover:text-ide-red ml-0.5 leading-none"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 min-h-0">
        {openTabs.length === 0 ? (
          <WelcomeScreen />
        ) : (
          <Editor
            height="100%"
            language={MONACO_LANG[language] ?? 'python'}
            value={displayContent}
            onChange={(val) => setEditorContent(val ?? '')}
            theme="vs-dark"
            options={{
              fontSize: 14,
              fontFamily: '"JetBrains Mono", "Fira Code", monospace',
              fontLigatures: true,
              lineHeight: 22,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              tabSize: 4,
              insertSpaces: true,
              automaticLayout: true,
              padding: { top: 16, bottom: 16 },
              smoothScrolling: true,
              cursorBlinking: 'phase',
              cursorSmoothCaretAnimation: 'on',
              renderLineHighlight: 'gutter',
              bracketPairColorization: { enabled: true },
              guides: { bracketPairs: true, indentation: true },
              suggest: { showWords: true },
              quickSuggestions: { other: true, comments: false, strings: false },
            }}
          />
        )}
      </div>
    </div>
  )
}

function WelcomeScreen() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-ide-dim select-none">
      <span className="text-5xl mb-4 opacity-30">🌌</span>
      <p className="text-sm font-semibold text-ide-muted">Nebula IDE</p>
      <p className="text-xs mt-1">Open a file from the explorer to start coding</p>
      <div className="mt-6 grid grid-cols-2 gap-2 text-2xs">
        {[
          ['▶', 'Run code'],
          ['✦', 'AI Review'],
          ['⌘S', 'Auto-saves'],
          ['+', 'New file'],
        ].map(([key, label]) => (
          <div key={key} className="flex items-center gap-2 bg-ide-elevated px-3 py-1.5 rounded border border-ide-border">
            <kbd className="font-mono text-ide-blue">{key}</kbd>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}