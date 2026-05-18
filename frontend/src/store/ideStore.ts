import { create } from 'zustand'
import type { Project, ProjectFile, ExecutionResult, ReviewResult, Language } from '@utils/api'

type PanelState = 'open' | 'closed'

interface EditorTab {
  fileId: string
  filename: string
  content: string
  isDirty: boolean
}

interface IDEState {
  // Project context
  currentProject: Project | null
  files: ProjectFile[]
  activeTab: EditorTab | null
  openTabs: EditorTab[]

  // Editor
  editorContent: string
  language: Language

  // Panels
  outputPanel: PanelState
  reviewPanel: PanelState
  sidebarOpen: boolean

  // Execution
  executionResult: ExecutionResult | null
  isExecuting: boolean
  executionError: string | null

  // Review
  reviewResult: ReviewResult | null
  isReviewing: boolean
  reviewError: string | null

  // Actions
  setProject: (project: Project) => void
  setFiles: (files: ProjectFile[]) => void
  openTab: (file: ProjectFile, content: string) => void
  closeTab: (fileId: string) => void
  setActiveTab: (fileId: string) => void
  updateTabContent: (fileId: string, content: string) => void
  markTabClean: (fileId: string) => void
  setEditorContent: (content: string) => void
  setLanguage: (lang: Language) => void

  setOutputPanel: (state: PanelState) => void
  setReviewPanel: (state: PanelState) => void
  toggleOutputPanel: () => void
  toggleReviewPanel: () => void
  setSidebarOpen: (open: boolean) => void

  setExecutionResult: (result: ExecutionResult | null) => void
  setExecuting: (v: boolean) => void
  setExecutionError: (e: string | null) => void

  setReviewResult: (result: ReviewResult | null) => void
  setReviewing: (v: boolean) => void
  setReviewError: (e: string | null) => void

  resetWorkspace: () => void
}

export const useIDEStore = create<IDEState>((set, get) => ({
  currentProject: null,
  files: [],
  activeTab: null,
  openTabs: [],
  editorContent: '',
  language: 'python',

  outputPanel: 'closed',
  reviewPanel: 'closed',
  sidebarOpen: true,

  executionResult: null,
  isExecuting: false,
  executionError: null,

  reviewResult: null,
  isReviewing: false,
  reviewError: null,

  setProject: (project) =>
    set({ currentProject: project, language: project.language as Language }),

  setFiles: (files) => set({ files }),

  openTab: (file, content) => {
    const existing = get().openTabs.find((t) => t.fileId === file.file_id)
    if (existing) {
      set({ activeTab: existing, editorContent: existing.content })
      return
    }
    const tab: EditorTab = {
      fileId: file.file_id,
      filename: file.filename,
      content,
      isDirty: false,
    }
    set((s) => ({
      openTabs: [...s.openTabs, tab],
      activeTab: tab,
      editorContent: content,
    }))
  },

  closeTab: (fileId) => {
    set((s) => {
      const tabs = s.openTabs.filter((t) => t.fileId !== fileId)
      const active = s.activeTab?.fileId === fileId
        ? tabs[tabs.length - 1] ?? null
        : s.activeTab
      return {
        openTabs: tabs,
        activeTab: active,
        editorContent: active?.content ?? '',
      }
    })
  },

  setActiveTab: (fileId) => {
    const tab = get().openTabs.find((t) => t.fileId === fileId)
    if (tab) set({ activeTab: tab, editorContent: tab.content })
  },

  updateTabContent: (fileId, content) => {
    set((s) => ({
      openTabs: s.openTabs.map((t) =>
        t.fileId === fileId ? { ...t, content, isDirty: true } : t
      ),
      activeTab: s.activeTab?.fileId === fileId
        ? { ...s.activeTab, content, isDirty: true }
        : s.activeTab,
      editorContent: content,
    }))
  },

  markTabClean: (fileId) => {
    set((s) => ({
      openTabs: s.openTabs.map((t) =>
        t.fileId === fileId ? { ...t, isDirty: false } : t
      ),
      activeTab: s.activeTab?.fileId === fileId
        ? { ...s.activeTab, isDirty: false }
        : s.activeTab,
    }))
  },

  setEditorContent: (content) => {
    const { activeTab } = get()
    if (activeTab) {
      get().updateTabContent(activeTab.fileId, content)
    } else {
      set({ editorContent: content })
    }
  },

  setLanguage: (lang) => set({ language: lang }),

  setOutputPanel: (state) => set({ outputPanel: state }),
  setReviewPanel: (state) => set({ reviewPanel: state }),
  toggleOutputPanel: () =>
    set((s) => ({ outputPanel: s.outputPanel === 'open' ? 'closed' : 'open' })),
  toggleReviewPanel: () =>
    set((s) => ({ reviewPanel: s.reviewPanel === 'open' ? 'closed' : 'open' })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setExecutionResult: (result) => set({ executionResult: result }),
  setExecuting: (v) => set({ isExecuting: v }),
  setExecutionError: (e) => set({ executionError: e }),

  setReviewResult: (result) => set({ reviewResult: result }),
  setReviewing: (v) => set({ isReviewing: v }),
  setReviewError: (e) => set({ reviewError: e }),

  resetWorkspace: () =>
    set({
      currentProject: null,
      files: [],
      activeTab: null,
      openTabs: [],
      editorContent: '',
      executionResult: null,
      reviewResult: null,
    }),
}))