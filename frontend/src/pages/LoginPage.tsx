import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@utils/api'
import { useAuthStore } from '@store/authStore'

type Mode = 'login' | 'signup'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'signup') {
        const { data } = await authApi.signup(email, username, password)
        setAuth({ user_id: data.user_id, email, username: data.username, role: data.role, created_at: '' }, data.access_token, data.refresh_token)
      } else {
        const { data } = await authApi.login(email, password)
        const { data: me } = await authApi.me()
        setAuth(me, data.access_token, data.refresh_token)
      }
      navigate('/dashboard')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail ?? 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ide-bg flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-ide-blue/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/3 w-64 h-64 bg-ide-purple/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🌌</div>
          <h1 className="text-xl font-bold text-ide-text">Nebula IDE</h1>
          <p className="text-sm text-ide-muted mt-1">AI-powered cloud development</p>
        </div>

        {/* Card */}
        <div className="bg-ide-surface border border-ide-border rounded-xl p-6 shadow-2xl">
          {/* Mode tabs */}
          <div className="flex mb-6 bg-ide-elevated rounded-lg p-1 border border-ide-border">
            {(['login', 'signup'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError('') }}
                className={`flex-1 py-1.5 text-sm rounded-md font-medium transition-all ${
                  mode === m
                    ? 'bg-ide-surface text-ide-text shadow border border-ide-border'
                    : 'text-ide-muted hover:text-ide-text'
                }`}
              >
                {m === 'login' ? 'Sign in' : 'Sign up'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-ide-muted mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full bg-ide-elevated border border-ide-border text-ide-text text-sm px-3 py-2 rounded-lg outline-none focus:border-ide-blue transition-colors placeholder-ide-dim"
              />
            </div>

            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-ide-muted mb-1.5">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="your_username"
                  className="w-full bg-ide-elevated border border-ide-border text-ide-text text-sm px-3 py-2 rounded-lg outline-none focus:border-ide-blue transition-colors placeholder-ide-dim"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-ide-muted mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={mode === 'signup' ? 'Min 8 chars, 1 uppercase, 1 digit' : '••••••••'}
                className="w-full bg-ide-elevated border border-ide-border text-ide-text text-sm px-3 py-2 rounded-lg outline-none focus:border-ide-blue transition-colors placeholder-ide-dim"
              />
            </div>

            {error && (
              <div className="rounded-lg bg-ide-red-dim border border-ide-red/30 px-3 py-2 text-xs text-ide-red">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-ide-blue hover:bg-ide-blue/90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Loading…</>
              ) : (
                mode === 'login' ? 'Sign in' : 'Create account'
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-2xs text-ide-dim mt-6">
          Secure sandboxed execution · AI code review · Cloud storage
        </p>
      </div>
    </div>
  )
}