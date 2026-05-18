import axios, { type AxiosInstance } from 'axios'

// ── Types ─────────────────────────────────────────────────────────────────────

export type Language = 'python' | 'javascript' | 'cpp'
export type Severity = 'error' | 'warning' | 'info'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  username: string
  role: string
}

export interface User {
  user_id: string
  email: string
  username: string
  role: string
  created_at: string
}

export interface Project {
  project_id: string
  user_id: string
  name: string
  language: Language
  description: string
  s3_prefix: string
  created_at: string
  updated_at: string
}

export interface ProjectFile {
  file_id: string
  project_id: string
  filename: string
  s3_key: string
  size_bytes: number
  updated_at: string
}

export interface FileContent extends ProjectFile {
  content: string
}

export interface ExecutionResult {
  exec_id: string
  stdout: string
  stderr: string
  exit_code: number
  runtime_ms: number
  timed_out: boolean
  language: Language
  executed_at: string
}

export interface Finding {
  line: number
  severity: Severity
  category: string
  rule_id: string
  message: string
  explanation: string
  fix: string | null
  source: string
}

export interface ReviewResult {
  review_id: string
  overall_score: number
  summary: string
  findings: Finding[]
  model_used: string
  tokens_used: number
  reviewed_at: string
  language: Language
}

// ── Axios instance ────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post<TokenResponse>(`${BASE_URL}/api/auth/refresh`, { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  signup: (email: string, username: string, password: string) =>
    api.post<TokenResponse>('/auth/signup', { email, username, password }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),

  me: () =>
    api.get<User>('/auth/me'),
}

// ── Projects ──────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: () =>
    api.get<{ projects: Project[] }>('/projects'),

  create: (name: string, language: Language, description = '') =>
    api.post<Project>('/projects', { name, language, description }),

  get: (id: string) =>
    api.get<Project>(`/projects/${id}`),

  update: (id: string, data: Partial<Pick<Project, 'name' | 'description'>>) =>
    api.put<Project>(`/projects/${id}`, data),

  delete: (id: string) =>
    api.delete(`/projects/${id}`),
}

// ── Files ─────────────────────────────────────────────────────────────────────

export const filesApi = {
  list: (projectId: string) =>
    api.get<{ files: ProjectFile[] }>(`/projects/${projectId}/files`),

  create: (projectId: string, filename: string, content = '') =>
    api.post<ProjectFile>(`/projects/${projectId}/files`, { filename, content }),

  getContent: (projectId: string, fileId: string) =>
    api.get<FileContent>(`/projects/${projectId}/files/${fileId}`),

  save: (projectId: string, fileId: string, content: string) =>
    api.put(`/projects/${projectId}/files/${fileId}`, { content }),

  delete: (projectId: string, fileId: string) =>
    api.delete(`/projects/${projectId}/files/${fileId}`),
}

// ── Execution ─────────────────────────────────────────────────────────────────

export const executeApi = {
  run: (code: string, language: Language, stdin = '', projectId?: string, fileId?: string) =>
    api.post<ExecutionResult>('/execute', { code, language, stdin, project_id: projectId, file_id: fileId }),

  history: () =>
    api.get<{ executions: ExecutionResult[] }>('/execute/history'),
}

// ── Review ────────────────────────────────────────────────────────────────────

export const reviewApi = {
  review: (code: string, language: Language, projectId?: string, fileId?: string) =>
    api.post<ReviewResult>('/review', { code, language, project_id: projectId, file_id: fileId }),
}

export default api