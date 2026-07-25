'use client'

import { useState, useEffect } from 'react'
import { Users, UserPlus, Key, Shield, Trash2, CheckCircle2, AlertCircle } from 'lucide-react'

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

  const API_BASE = '/api/v1'

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
    return <div className="p-8 text-center text-slate-400 text-xs">Carregando usuários...</div>
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-amber-400" /> Gestão de Usuários (Multi-tenant)
            </h2>
            <p className="text-xs text-slate-400">Adicione, bloqueie ou redefina credenciais de acesso.</p>
          </div>
        </div>

        {message && (
          <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/40 p-2.5 rounded-xl border border-emerald-500/20">
            <CheckCircle2 className="w-4 h-4 shrink-0" /> {message}
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-950/40 p-2.5 rounded-xl border border-rose-500/20">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        {/* Create User Form */}
        <form onSubmit={handleCreateUser} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
          <h3 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
            <UserPlus className="w-3.5 h-3.5 text-indigo-400" /> Novo Usuário
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="email"
              placeholder="E-mail"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <input
              type="password"
              placeholder="Senha (mín. 6 caracteres)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-lg px-3 py-2">
              <span className="text-xs text-slate-300">Administrador</span>
              <input
                type="checkbox"
                checked={newIsAdmin}
                onChange={(e) => setNewIsAdmin(e.target.checked)}
                className="w-4 h-4 rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 text-xs shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50"
          >
            {creating ? 'Criando...' : 'Cadastrar Novo Usuário'}
          </button>
        </form>

        {/* Users List */}
        <div className="space-y-2.5">
          <h3 className="text-xs font-semibold text-slate-300">Usuários Cadastrados ({users.length})</h3>
          {users.map((u) => (
            <div key={u.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white">{u.email}</span>
                  {u.is_admin === 1 && (
                    <span className="text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Admin
                    </span>
                  )}
                  {u.is_active === 1 ? (
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
                      Ativo
                    </span>
                  ) : (
                    <span className="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded-full font-medium">
                      Bloqueado
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500">ID: {u.id}</p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {resetUserId === u.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      placeholder="Nova senha"
                      value={resetPasswordValue}
                      onChange={(e) => setResetPasswordValue(e.target.value)}
                      className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 w-32 focus:outline-none"
                    />
                    <button
                      onClick={() => handleResetPassword(u.id)}
                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium"
                    >
                      Salvar
                    </button>
                    <button
                      onClick={() => { setResetUserId(null); setResetPasswordValue('') }}
                      className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
                    >
                      X
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setResetUserId(u.id)}
                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center gap-1"
                  >
                    <Key className="w-3 h-3" /> Nova Senha
                  </button>
                )}

                <button
                  onClick={() => handleRegenerateKey(u.id)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-400 rounded-lg text-xs font-medium"
                  title="Gerar nova API Key"
                >
                  API Key
                </button>

                <button
                  onClick={() => handleToggleActive(u.id, u.is_active)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium ${
                    u.is_active === 1
                      ? 'bg-rose-950/40 text-rose-400 border border-rose-500/20 hover:bg-rose-900/50'
                      : 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-900/50'
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
