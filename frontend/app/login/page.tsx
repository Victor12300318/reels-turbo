'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Lock, Mail, Sparkles } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Falha ao realizar login')
      }

      const data = await res.json()
      localStorage.setItem('reels_api_key', data.api_key)
      localStorage.setItem('reels_user_email', data.email)
      router.push('/')
    } catch (err: any) {
      setError(err.message || 'Erro de conexão com a API')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-md space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm hover:shadow-md transition-all">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 text-[#0066FF] mb-2">
            <Sparkles className="w-6 h-6 text-[#0066FF]" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Clonify AI</h1>
          <p className="text-sm text-slate-500">Acesse o seu painel de automação de Reels</p>
        </div>

        {error && (
          <div className="rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">E-mail</label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                placeholder="seu@email.com"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Senha</label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-[#0066FF] hover:bg-blue-700 py-3 text-sm font-bold text-white shadow-sm shadow-blue-600/20 disabled:opacity-50 transition-all"
          >
            {loading ? 'Entrando...' : 'Entrar no Painel'}
          </button>
        </form>
      </div>
    </div>
  )
}