'use client'

import { useState, useEffect } from 'react'
import { Users, UserPlus, Key, Shield, Trash2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react'

interface User {
  id: string
  email: string
  is_admin: number
  is_active: number
  api_key?: string
  created_at?: string
}

export default function UserManagementTab({ apiKey }: { apiKey: string }) {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  // New user modal/form state
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newIsAdmin, setNewIsAdmin] = useState(false)
  const [creating, setCreating] = useState(false)

  // Reset password modal state
  const [resetUserId, setResetUserId] = useState<string | null>(null)
  const [resetPasswordValue, setResetPasswordValue] = useState('')

  // System AI Settings state (Admin only)
  const [aiProvider, setAiProvider] = useState<'gemini' | 'openrouter'>('gemini')
  const [openrouterApiKey, setOpenrouterApiKey] = useState('')
  const [openrouterModel, setOpenrouterModel] = useState('google/gemini-2.0-flash-001')
  const [aiSaving, setAiSaving] = useState(false)
  const [aiMessage, setAiMessage] = useState('')

  const API_BASE = '/api/v1'

  const fetchSystemSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/settings`, {
        headers: { 'X-API-Key': apiKey }
      })
      if (res.ok) {
        const data = await res.json()
        setAiProvider(data.ai_provider || 'gemini')
        setOpenrouterApiKey(data.openrouter_api_key || '')
        setOpenrouterModel(data.openrouter_model || 'google/gemini-2.0-flash-001')
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleSaveAiSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setAiSaving(true)
    setAiMessage('')
    try {
      const res = await fetch(`${API_BASE}/admin/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          ai_provider: aiProvider,
          openrouter_api_key: openrouterApiKey,
          openrouter_model: openrouterModel
        })
      })
      const data = await res.json()
      if (res.ok) {
        setAiMessage('Configurações de IA salvas com sucesso!')
      } else {
        setAiMessage(`Erro: ${data.detail || 'Falha ao salvar'}`)
      }
    } catch (err: any) {
      setAiMessage(`Erro: ${err.message}`)
    } finally {
      setAiSaving(false)
      setTimeout(() => setAiMessage(''), 4000)
    }
  }

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/users`, {
        headers: { 'X-API-Key': apiKey }
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users)
      } else {
        const err = await res.json()
        setError(err.detail || 'Falha ao carregar usuários')
      }
    } catch (e: any) {
      setError(e.message || 'Erro de conexão')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
    fetchSystemSettings()
  }, [apiKey])

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEmail || !newPassword) return
    setCreating(true)
    setMessage('')
    setError('')

    try {
      const res = await fetch(`${API_BASE}/admin/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({
          email: newEmail,
          password: newPassword,
          is_admin: newIsAdmin ? 1 : 0
        })
      })
      const data = await res.json()
      if (res.ok) {
        setMessage('Usuário criado com sucesso!')
        setNewEmail('')
        setNewPassword('')
        setNewIsAdmin(false)
        fetchUsers()
      } else {
        throw new Error(data.detail || 'Erro ao criar usuário')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCreating(false)
      setTimeout(() => { setMessage(''); setError('') }, 4000)
    }
  }

  const handleToggleActive = async (userId: string, currentActive: number) => {
    const newActive = currentActive === 1 ? 0 : 1
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/toggle-active`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ is_active: newActive })
      })
      const data = await res.json()
      if (res.ok) {
        setUsers(users.map(u => u.id === userId ? { ...u, is_active: newActive } : u))
      } else {
        alert(data.detail || 'Falha ao atualizar status')
      }
    } catch (e: any) {
      alert(e.message)
    }
  }

  const handleResetPassword = async (userId: string) => {
    if (!resetPasswordValue || resetPasswordValue.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres.')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ password: resetPasswordValue })
      })
      const data = await res.json()
      if (res.ok) {
        alert('Senha redefinida com sucesso!')
        setResetUserId(null)
        setResetPasswordValue('')
      } else {
        alert(data.detail || 'Falha ao redefinir senha')
      }
    } catch (e: any) {
      alert(e.message)
    }
  }

  const handleRegenerateKey = async (userId: string) => {
    if (!confirm('Deseja realmente gerar uma nova API Key para este usuário?')) return
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/regenerate-key`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey }
      })
      const data = await res.json()
      if (res.ok) {
        alert(`Nova API Key gerada:\n\n${data.api_key}\n\nCopie agora, ela não será exibida novamente.`)
      } else {
        alert(data.detail || 'Falha ao regenerar chave')
      }
    } catch (e: any) {
      alert(e.message)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500 text-xs">Carregando usuários...</div>
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5 shadow-sm hover:shadow-md transition-all">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-[#0066FF]" /> Gestão de Usuários (Multi-tenant)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Adicione, bloqueie ou redefina credenciais de acesso.</p>
          </div>
        </div>

        {message && (
          <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 p-3 rounded-xl border border-emerald-200">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" /> {message}
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-rose-800 bg-rose-50 p-3 rounded-xl border border-rose-200">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" /> {error}
          </div>
        )}

        {/* System AI Provider Configuration (Admin) */}
        <form onSubmit={handleSaveAiSettings} className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
          <h3 className="text-xs font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-[#0066FF]" /> Provedor de Inteligência Artificial (Admin)
          </h3>
          <p className="text-[11px] text-slate-500">Selecione o provedor de IA utilizado globalmente no sistema para análise e seleção de vídeos.</p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Provedor Ativo</label>
              <select
                value={aiProvider}
                onChange={(e) => setAiProvider(e.target.value as any)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-[#0066FF]"
              >
                <option value="gemini">Google Gemini (Default SDK)</option>
                <option value="openrouter">OpenRouter (Multi-Model API)</option>
              </select>
            </div>

            {aiProvider === 'openrouter' && (
              <>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">OpenRouter API Key</label>
                  <input
                    type="password"
                    placeholder="sk-or-v1-..."
                    value={openrouterApiKey}
                    onChange={(e) => setOpenrouterApiKey(e.target.value)}
                    required={aiProvider === 'openrouter'}
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-[#0066FF]"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">Modelo OpenRouter</label>
                  <input
                    type="text"
                    placeholder="google/gemini-2.0-flash-001"
                    value={openrouterModel}
                    onChange={(e) => setOpenrouterModel(e.target.value)}
                    required={aiProvider === 'openrouter'}
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-[#0066FF]"
                  />
                </div>
              </>
            )}
          </div>

          {aiMessage && (
            <p className="text-xs text-blue-800 bg-blue-50 p-2.5 rounded-lg border border-blue-200">{aiMessage}</p>
          )}

          <button
            type="submit"
            disabled={aiSaving}
            className="w-full rounded-lg bg-[#0066FF] hover:bg-blue-700 text-white font-bold py-2 text-xs shadow-sm shadow-blue-600/20 transition-all disabled:opacity-50"
          >
            {aiSaving ? 'Salvando...' : 'Salvar Configurações de IA'}
          </button>
        </form>

        {/* Create User Form */}
        <form onSubmit={handleCreateUser} className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
          <h3 className="text-xs font-bold text-slate-800 flex items-center gap-2">
            <UserPlus className="w-3.5 h-3.5 text-[#0066FF]" /> Novo Usuário
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="email"
              placeholder="E-mail"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
              className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0066FF]"
            />
            <input
              type="password"
              placeholder="Senha (mín. 6 caracteres)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0066FF]"
            />
            <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-slate-700">Administrador</span>
              <input
                type="checkbox"
                checked={newIsAdmin}
                onChange={(e) => setNewIsAdmin(e.target.checked)}
                className="w-4 h-4 rounded text-[#0066FF] focus:ring-0 cursor-pointer accent-[#0066FF]"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="w-full rounded-lg bg-[#0066FF] hover:bg-blue-700 text-white font-bold py-2.5 text-xs shadow-sm shadow-blue-600/20 transition-all disabled:opacity-50"
          >
            {creating ? 'Criando...' : 'Cadastrar Novo Usuário'}
          </button>
        </form>

        {/* Users List */}
        <div className="space-y-2.5">
          <h3 className="text-xs font-bold text-slate-700">Usuários Cadastrados ({users.length})</h3>
          {users.map((u) => (
            <div key={u.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-white transition-all">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900">{u.email}</span>
                  {u.is_admin === 1 && (
                    <span className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-full font-bold flex items-center gap-1">
                      <Shield className="w-3 h-3 text-amber-600" /> Admin
                    </span>
                  )}
                  {u.is_active === 1 ? (
                    <span className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded-full font-bold">
                      Ativo
                    </span>
                  ) : (
                    <span className="text-[10px] bg-rose-50 text-rose-800 border border-rose-200 px-2 py-0.5 rounded-full font-bold">
                      Bloqueado
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 font-mono">ID: {u.id}</p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {resetUserId === u.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      placeholder="Nova senha"
                      value={resetPasswordValue}
                      onChange={(e) => setResetPasswordValue(e.target.value)}
                      className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-900 w-32 focus:outline-none"
                    />
                    <button
                      onClick={() => handleResetPassword(u.id)}
                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold"
                    >
                      Salvar
                    </button>
                    <button
                      onClick={() => { setResetUserId(null); setResetPasswordValue('') }}
                      className="px-2 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs"
                    >
                      X
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setResetUserId(u.id)}
                    className="px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold flex items-center gap-1"
                  >
                    <Key className="w-3 h-3 text-slate-500" /> Nova Senha
                  </button>
                )}

                <button
                  onClick={() => handleRegenerateKey(u.id)}
                  className="px-2.5 py-1 bg-white hover:bg-slate-100 text-[#0066FF] border border-slate-200 rounded-lg text-xs font-semibold"
                  title="Gerar nova API Key"
                >
                  API Key
                </button>

                <button
                  onClick={() => handleToggleActive(u.id, u.is_active)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    u.is_active === 1
                      ? 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                  }`}
                >
                  {u.is_active === 1 ? 'Bloquear' : 'Ativar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}