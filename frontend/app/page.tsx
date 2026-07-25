'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  Copy,
  Check,
  Upload,
  Video,
  Smartphone,
  ExternalLink,
  Download,
  RefreshCw,
  Sparkles,
  LogOut,
  AlertCircle,
  FileVideo,
  Calendar as CalendarIcon,
  Settings,
  Layers,
  Send,
  Trash2,
  Play,
  Eye,
  Clock,
  Zap,
  Users,
  CheckCircle2,
  Key,
  Shield,
  UserPlus,
  Lock,
  Menu
} from 'lucide-react'

import UserManagementTab from '../components/UserManagementTab'

interface Job {
  id: string
  url: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'scheduled'
  progress: number
  output_path: string
  original_s3_url?: string
  error?: string
  caption?: string
  scheduled_at?: string
  posted_at?: string
  share_to_feed?: number
  created_at: string
}

interface LocalVideo {
  id: number
  filename: string
  path: string
  description?: string
  themes?: string
  duration_seconds?: number
  updated_at?: string
}

interface Metrics {
  total_cloned: number
  total_published: number
  library_count: number
  scheduled_count: number
}

export default function DashboardPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'cloner' | 'calendar' | 'editor' | 'library' | 'users'>('cloner')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  // Auth & Settings state
  const [apiKey, setApiKey] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Custom Settings
  const [defaultCaptionSuffix, setDefaultCaptionSuffix] = useState('')
  const [shareToFeed, setShareToFeed] = useState(false)
  const [intervalHours, setIntervalHours] = useState(3)
  const [settingsSaving, setIgSaving] = useState(false)
  const [settingsMessage, setSettingsMessage] = useState('')

  // Meta Instagram state
  const [igAccountId, setIgAccountId] = useState('')
  const [igAccessToken, setIgAccessToken] = useState('')

  // Data state
  const [jobs, setJobs] = useState<Job[]>([])
  const [videos, setVideos] = useState<LocalVideo[]>([])
  const [metrics, setMetrics] = useState<Metrics>({ total_cloned: 0, total_published: 0, library_count: 0, scheduled_count: 0 })
  const [loading, setLoading] = useState(true)

  // Player comparison state (job_id -> 'ia' | 'original')
  const [playerMode, setPlayerMode] = useState<Record<string, 'ia' | 'original'>>({})

  // Batch Scheduling state
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([])
  const [batchInterval, setBatchInterval] = useState(3)
  const [batchMessage, setBatchMessage] = useState('')
  const [batchScheduling, setBatchScheduling] = useState(false)

  // Upload state
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')

  // Direct Clone Input state
  const [inputUrl, setInputUrl] = useState('')
  const [cloningNow, setCloningNow] = useState(false)

  // Cookie state
  const [cookieStatus, setCookieStatus] = useState<'active' | 'missing'>('missing')
  const [cookieMessage, setCookieMessage] = useState('')
  const [cookieUploading, setCookieUploading] = useState(false)

  // Edit Schedule Modal state
  const [editingJob, setEditingJob] = useState<Job | null>(null)
  const [newScheduleTime, setNewScheduleTime] = useState('')
  const [savingSchedule, setSavingSchedule] = useState(false)

  const completedJobIdsRef = useRef<Set<string>>(new Set())
  const API_BASE = '/api/v1'

  useEffect(() => {
    const key = localStorage.getItem('reels_api_key')
    const email = localStorage.getItem('reels_user_email')
    if (!key) {
      router.push('/login')
      return
    }
    setApiKey(key)
    setUserEmail(email || '')

    // Restore active tab from URL search param or localStorage
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const urlTab = params.get('tab') as any
      const savedTab = localStorage.getItem('reels_active_tab') as any
      const validTabs = ['cloner', 'calendar', 'editor', 'library', 'users']

      if (urlTab && validTabs.includes(urlTab)) {
        setActiveTab(urlTab)
      } else if (savedTab && validTabs.includes(savedTab)) {
        setActiveTab(savedTab)
      }
    }

    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }

    fetchInitialData(key)
  }, [router])

  // Polling effect
  useEffect(() => {
    if (!apiKey) return
    const hasActiveJobs = jobs.some(j => j.status === 'processing' || j.status === 'pending')
    const pollIntervalMs = hasActiveJobs ? 6000 : 30000

    const interval = setInterval(() => {
      fetchJobs(apiKey)
    }, pollIntervalMs)

    return () => clearInterval(interval)
  }, [apiKey, jobs.map(j => j.status).join(',')])

  const changeTab = (tab: 'cloner' | 'calendar' | 'editor' | 'library' | 'users') => {
    setActiveTab(tab)
    if (typeof window !== 'undefined') {
      localStorage.setItem('reels_active_tab', tab)
      const url = new URL(window.location.href)
      url.searchParams.set('tab', tab)
      window.history.replaceState(null, '', url.toString())
    }
  }

  const fetchInitialData = async (key: string) => {
    setLoading(true)
    await Promise.all([fetchJobs(key), fetchVideos(key), fetchUserInfo(key), fetchMetrics(key), fetchCookiesStatus(key)])
    setLoading(false)
  }

  const fetchCookiesStatus = async (key: string) => {
    try {
      const res = await fetch(`${API_BASE}/admin/cookies/status`, { headers: { 'X-API-Key': key } })
      if (res.ok) {
        const data = await res.json()
        setCookieStatus(data.status)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleCookiesUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setCookieUploading(true)
    setCookieMessage('Enviando cookies.txt...')
    const formData = new FormData()
    formData.append('file', files[0])

    try {
      const res = await fetch(`${API_BASE}/admin/cookies`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
        body: formData
      })
      const data = await res.json()
      if (res.ok) {
        setCookieMessage(data.message)
        await fetchCookiesStatus(apiKey)
      } else {
        throw new Error(data.detail || 'Falha ao salvar cookies')
      }
    } catch (err: any) {
      setCookieMessage(`Erro: ${err.message}`)
    } finally {
      setCookieUploading(false)
      setTimeout(() => setCookieMessage(''), 4000)
    }
  }

  const fetchUserInfo = async (key: string) => {
    try {
      const res = await fetch(`${API_BASE}/user/me`, { headers: { 'X-API-Key': key } })
      if (res.ok) {
        const data = await res.json()
        setIgAccountId(data.instagram_account_id || '')
        setIgAccessToken(data.instagram_access_token || '')
        setDefaultCaptionSuffix(data.default_caption_suffix || '')
        setShareToFeed(Boolean(data.share_to_feed))
        setIntervalHours(data.default_post_interval_hours || 3)
        setIsAdmin(Boolean(data.is_admin))
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchJobs = async (key: string) => {
    try {
      const res = await fetch(`${API_BASE}/jobs`, { headers: { 'X-API-Key': key } })
      if (res.ok) {
        const data = await res.json()
        const newJobs: Job[] = data.jobs || []
        setJobs(newJobs)

        const totalCloned = newJobs.filter(j => j.status === 'completed' || j.status === 'scheduled').length
        const totalPublished = newJobs.filter(j => j.posted_at || j.status === 'completed').length
        const scheduledCount = newJobs.filter(j => j.status === 'scheduled').length

        setMetrics(prev => ({
          ...prev,
          total_cloned: totalCloned,
          total_published: totalPublished,
          scheduled_count: scheduledCount
        }))

        newJobs.forEach((job) => {
          if (job.status === 'completed' && !completedJobIdsRef.current.has(job.id)) {
            completedJobIdsRef.current.add(job.id)
            notifyBrowser(job)
          }
        })
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchVideos = async (key: string) => {
    try {
      const res = await fetch(`${API_BASE}/videos`, { headers: { 'X-API-Key': key } })
      if (res.ok) {
        const data = await res.json()
        setVideos(data.videos || [])
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchMetrics = async (key: string) => {
    try {
      const res = await fetch(`${API_BASE}/metrics`, { headers: { 'X-API-Key': key } })
      if (res.ok) {
        const data = await res.json()
        setMetrics(data)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const notifyBrowser = (job: Job) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Reels Clonado com Sucesso', {
        body: 'Seu vídeo foi renderizado e está pronto no seu painel.',
        icon: '/favicon.ico'
      })
    }
  }

  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setIgSaving(true)
    setSettingsMessage('')
    try {
      const res = await fetch(`${API_BASE}/user/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          default_caption_suffix: defaultCaptionSuffix,
          share_to_feed: shareToFeed,
          default_post_interval_hours: intervalHours
        })
      })

      if (igAccountId && igAccessToken) {
        await fetch(`${API_BASE}/user/instagram`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
          body: JSON.stringify({ instagram_account_id: igAccountId, instagram_access_token: igAccessToken })
        })
      }

      if (res.ok) {
        setSettingsMessage('Configurações salvas com sucesso!')
      }
    } catch (err: any) {
      setSettingsMessage(`Erro: ${err.message}`)
    } finally {
      setIgSaving(false)
      setTimeout(() => setSettingsMessage(''), 4000)
    }
  }

  const handleCreateClone = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputUrl) return
    setCloningNow(true)
    try {
      const res = await fetch(`${API_BASE}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ url: inputUrl })
      })
      if (res.ok) {
        setInputUrl('')
        await fetchJobs(apiKey)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setCloningNow(false)
    }
  }

  const handlePublishNow = async (jobId: string) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ share_to_feed: shareToFeed })
      })
      const data = await res.json()
      if (res.ok) {
        alert('Reels publicado no Instagram com sucesso!')
        await fetchJobs(apiKey)
      } else {
        alert(`Erro ao publicar: ${data.detail || 'Falha no envio'}`)
      }
    } catch (e: any) {
      alert(`Erro de conexão: ${e.message}`)
    }
  }

  const handleBatchSchedule = async () => {
    if (selectedJobIds.length === 0) {
      alert('Selecione ao menos 1 Reels para agendar.')
      return
    }
    setBatchScheduling(true)
    try {
      const res = await fetch(`${API_BASE}/jobs/batch-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          job_ids: selectedJobIds,
          interval_hours: batchInterval,
          share_to_feed: shareToFeed
        })
      })
      const data = await res.json()
      if (res.ok) {
        setBatchMessage(data.message)
        setSelectedJobIds([])
        await fetchJobs(apiKey)
      }
    } catch (e: any) {
      setBatchMessage(`Erro: ${e.message}`)
    } finally {
      setBatchScheduling(false)
      setTimeout(() => setBatchMessage(''), 4000)
    }
  }

  const handleDeleteVideo = async (videoId: number) => {
    if (!confirm('Deseja remover este vídeo da sua biblioteca?')) return
    try {
      await fetch(`${API_BASE}/videos/${videoId}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': apiKey }
      })
      await fetchVideos(apiKey)
    } catch (e) {
      console.error(e)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setUploading(true)

    const fileList = Array.from(files).slice(0, 30)
    const total = fileList.length
    let completedCount = 0
    let successCount = 0

    setUploadMessage(`Iniciando upload de ${total} vídeo(s)... (0/${total})`)

    const uploadSingleFile = async (file: File) => {
      let attempts = 0
      const maxAttempts = 3
      while (attempts < maxAttempts) {
        attempts++
        try {
          const res = await fetch(`${API_BASE}/videos/upload-stream?filename=${encodeURIComponent(file.name)}`, {
            method: 'POST',
            headers: {
              'X-API-Key': apiKey,
              'Content-Type': file.type || 'video/mp4'
            },
            body: file
          })
          if (res.ok) {
            successCount++
            break
          }
        } catch (err: any) {
          console.error(`Erro ao enviar ${file.name} (tentativa ${attempts}/${maxAttempts}):`, err)
          if (attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 1000))
          }
        }
      }
      completedCount++
      setUploadMessage(`Enviando vídeos para S3... (${completedCount}/${total} concluído(s))`)
    }

    const queue = [...fileList]
    const activeWorkers: Promise<void>[] = []
    const CONCURRENCY_LIMIT = 3

    while (queue.length > 0 || activeWorkers.length > 0) {
      while (queue.length > 0 && activeWorkers.length < CONCURRENCY_LIMIT) {
        const nextFile = queue.shift()!
        const promise: Promise<void> = uploadSingleFile(nextFile).then(() => {
          const idx = activeWorkers.indexOf(promise)
          if (idx !== -1) activeWorkers.splice(idx, 1)
        })
        activeWorkers.push(promise)
      }
      if (activeWorkers.length > 0) {
        await Promise.race(activeWorkers)
      }
    }

    if (successCount > 0) {
      setUploadMessage(`${successCount} de ${total} vídeo(s) enviado(s) para o S3 com sucesso!`)
      await fetchVideos(apiKey)
    } else {
      setUploadMessage('Falha ao enviar os vídeos para o S3. Tente novamente.')
    }

    setUploading(false)
    setTimeout(() => setUploadMessage(''), 5000)
  }

  const toggleJobSelection = (id: string) => {
    setSelectedJobIds(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id])
  }

  const handleLogout = () => {
    localStorage.removeItem('reels_api_key')
    localStorage.removeItem('reels_user_email')
    localStorage.removeItem('reels_active_tab')
    router.push('/login')
  }

  const openEditScheduleModal = (job: Job) => {
    setEditingJob(job)
    if (job.scheduled_at) {
      try {
        const dt = new Date(job.scheduled_at)
        const formatted = dt.toISOString().slice(0, 16)
        setNewScheduleTime(formatted)
      } catch (e) {
        setNewScheduleTime('')
      }
    } else {
      setNewScheduleTime('')
    }
  }

  const handleUpdateScheduleTime = async () => {
    if (!editingJob || !newScheduleTime) return
    setSavingSchedule(true)
    try {
      const res = await fetch(`${API_BASE}/jobs/${editingJob.id}/schedule`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ scheduled_at: newScheduleTime })
      })
      const data = await res.json()
      if (res.ok) {
        alert('Horário de agendamento atualizado com sucesso!')
        setEditingJob(null)
        await fetchJobs(apiKey)
      } else {
        alert(`Erro ao atualizar: ${data.detail || 'Falha na requisição'}`)
      }
    } catch (e: any) {
      alert(`Erro de conexão: ${e.message}`)
    } finally {
      setSavingSchedule(false)
    }
  }

  const handleCancelSchedule = async () => {
    if (!editingJob) return
    if (!confirm('Deseja realmente cancelar este agendamento? O vídeo retornará ao status de Pronto.')) return
    setSavingSchedule(true)
    try {
      const res = await fetch(`${API_BASE}/jobs/${editingJob.id}/schedule`, {
        method: 'DELETE',
        headers: { 'X-API-Key': apiKey }
      })
      const data = await res.json()
      if (res.ok) {
        alert('Agendamento cancelado com sucesso!')
        setEditingJob(null)
        await fetchJobs(apiKey)
      } else {
        alert(`Erro ao cancelar: ${data.detail || 'Falha na requisição'}`)
      }
    } catch (e: any) {
      alert(`Erro de conexão: ${e.message}`)
    } finally {
      setSavingSchedule(false)
    }
  }

  const formatScheduledTime = (isoString?: string) => {
    if (!isoString) return 'Em breve'
    try {
      const date = new Date(isoString)
      const today = new Date()
      const isToday = date.toDateString() === today.toDateString()
      const timeStr = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
      if (isToday) {
        return `Hoje às ${timeStr}`
      }
      const dateStr = date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
      return `${dateStr} às ${timeStr}`
    } catch (e) {
      return 'Agendado'
    }
  }

  const navItems = [
    { id: 'cloner', label: 'Clonador', icon: Zap },
    { id: 'calendar', label: 'Agenda', icon: CalendarIcon },
    { id: 'editor', label: 'Ajustes', icon: Settings },
    { id: 'library', label: 'Biblioteca', icon: Video },
    ...(isAdmin ? [{ id: 'users', label: 'Usuários', icon: Users }] : [])
  ] as const

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased flex flex-col md:flex-row">
      
      {/* DESKTOP SIDEBAR NAVIGATION (MANYCHAT LIGHT SAAS STYLE) */}
      <aside
        className={`hidden md:flex flex-col fixed top-0 left-0 bottom-0 z-40 bg-white border-r border-slate-200 transition-all duration-300 shadow-sm ${
          sidebarCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* SIDEBAR HEADER WITH HAMBURGER TOGGLE */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center font-bold">
                <Sparkles className="w-5 h-5 text-[#0066FF]" />
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight text-slate-900 leading-tight">Reels Cloner</h1>
                <p className="text-[10px] text-blue-600 font-medium">ManyChat Edition</p>
              </div>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center mx-auto">
              <Sparkles className="w-5 h-5 text-[#0066FF]" />
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-2 text-slate-500 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-all"
            title={sidebarCollapsed ? 'Expandir Menu' : 'Recolher Menu'}
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        {/* NAVIGATION ITEMS */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <button
                key={item.id}
                onClick={() => changeTab(item.id as any)}
                title={sidebarCollapsed ? item.label : undefined}
                className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl font-semibold text-xs transition-all duration-200 ${
                  isActive
                    ? 'bg-[#0066FF] text-white shadow-sm shadow-blue-600/20'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                } ${sidebarCollapsed ? 'justify-center px-0' : ''}`}
              >
                <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* SIDEBAR FOOTER (USER & LOGOUT) */}
        <div className="p-4 border-t border-slate-100">
          {!sidebarCollapsed ? (
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-900 truncate">{userEmail || 'Usuário'}</p>
                <p className="text-[10px] text-slate-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Ativo
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-slate-100 transition-all"
                title="Sair da Conta"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="w-full flex justify-center p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-slate-100 transition-all"
              title="Sair da Conta"
            >
              <LogOut className="w-5 h-5" />
            </button>
          )}
        </div>
      </aside>

      {/* MOBILE TOP HEADER */}
      <header className="md:hidden sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 text-[#0066FF] flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-slate-900 leading-tight">Reels Cloner</h1>
            <p className="text-[10px] text-slate-500 truncate max-w-[160px]">{userEmail}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="p-2 text-slate-500 hover:text-slate-900 rounded-lg">
          <LogOut className="w-4 h-4" />
        </button>
      </header>

      {/* MAIN CONTAINER (RESPONSIVE GRID & 3D ELEVATION CARDS) */}
      <main
        className={`flex-1 transition-all duration-300 ${
          sidebarCollapsed ? 'md:pl-20' : 'md:pl-64'
        } pb-28 md:pb-12`}
      >
        <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">

          {/* DASHBOARD TOP HEADER BAR & METRICS */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                {activeTab === 'cloner' && <>Clonador de Reels</>}
                {activeTab === 'calendar' && <>Agenda de Publicações</>}
                {activeTab === 'editor' && <>Configurações & Integração</>}
                {activeTab === 'library' && <>Biblioteca de Vídeos Locais</>}
                {activeTab === 'users' && <>Gestão de Usuários</>}
              </h2>
              <p className="text-xs md:text-sm text-slate-500 mt-1">
                Automação de conteúdo visual para o Instagram no padrão ManyChat.
              </p>
            </div>

            {/* METRICS SUMMARY BADGES */}
            <div className="grid grid-cols-4 gap-2.5 md:flex md:items-center">
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-center md:text-left shadow-sm">
                <p className="text-base md:text-lg font-extrabold text-[#0066FF] leading-tight">{metrics.total_cloned}</p>
                <p className="text-[9px] text-slate-500 uppercase font-bold">Clonados</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-center md:text-left shadow-sm">
                <p className="text-base md:text-lg font-extrabold text-emerald-600 leading-tight">{metrics.total_published}</p>
                <p className="text-[9px] text-slate-500 uppercase font-bold">Postados</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-center md:text-left shadow-sm">
                <p className="text-base md:text-lg font-extrabold text-amber-600 leading-tight">{metrics.scheduled_count}</p>
                <p className="text-[9px] text-slate-500 uppercase font-bold">Agendados</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-center md:text-left shadow-sm">
                <p className="text-base md:text-lg font-extrabold text-slate-700 leading-tight">{metrics.library_count}</p>
                <p className="text-[9px] text-slate-500 uppercase font-bold">Biblioteca</p>
              </div>
            </div>
          </div>

          {/* TAB 1: CLONADOR (HOME FEED) */}
          {activeTab === 'cloner' && (
            <div className="space-y-6">
              
              {/* MANUAL URL INPUT */}
              <form onSubmit={handleCreateClone} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-all">
                <label className="text-xs font-bold text-slate-900 flex items-center gap-2 uppercase tracking-wide">
                  <Zap className="w-4 h-4 text-[#0066FF]" /> Clonar Link do Instagram Reels
                </label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="url"
                    required
                    value={inputUrl}
                    onChange={(e) => setInputUrl(e.target.value)}
                    placeholder="https://www.instagram.com/reel/..."
                    className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs md:text-sm text-slate-900 placeholder-slate-400 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                  />
                  <button
                    type="submit"
                    disabled={cloningNow}
                    className="rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white px-6 py-2.5 text-xs md:text-sm font-bold shrink-0 shadow-sm shadow-blue-600/20 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" />
                    {cloningNow ? 'Processando...' : 'Clonar Reels'}
                  </button>
                </div>
              </form>

              {/* JOBS FEED - RESPONSIVE GRID (1, 2, 3 COLUMNS WITH 3D HOVER ELEVATION) */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Seus Reels Processados</h3>
                  <button onClick={() => fetchJobs(apiKey)} className="text-xs text-[#0066FF] hover:text-blue-700 flex items-center gap-1 font-semibold transition-all">
                    <RefreshCw className="w-3.5 h-3.5" /> Atualizar
                  </button>
                </div>

                {jobs.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 p-12 text-center space-y-3 bg-white">
                    <Sparkles className="w-10 h-10 text-slate-300 mx-auto" />
                    <p className="text-sm font-semibold text-slate-700">Nenhum Reels clonado ainda.</p>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto">Cole um link no campo acima para gerar um novo Reels a partir da sua biblioteca local.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {jobs.map((job) => {
                      const currentMode = playerMode[job.id] || 'ia'
                      const videoSrc = currentMode === 'ia' ? job.output_path : (job.original_s3_url || job.url)
                      const isReadyOrScheduled = (job.status === 'completed' || job.status === 'scheduled') && Boolean(job.output_path)

                      return (
                        <div key={job.id} className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3.5 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between">
                          {/* CARD STATUS BADGE */}
                          <div className="space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-[11px] font-mono text-slate-600 truncate max-w-[180px]" title={job.url}>
                                {job.url}
                              </span>
                              {job.status === 'completed' && (
                                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 shrink-0">
                                  <CheckCircle2 className="w-3 h-3" /> Pronto
                                </span>
                              )}
                              {job.status === 'scheduled' && (
                                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1 shrink-0" title={job.scheduled_at}>
                                  <Clock className="w-3 h-3" /> Agendado ({formatScheduledTime(job.scheduled_at)})
                                </span>
                              )}
                              {job.status === 'processing' && (
                                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-50 text-[#0066FF] border border-blue-200 animate-pulse flex items-center gap-1 shrink-0">
                                  <RefreshCw className="w-3 h-3 animate-spin" /> {job.progress || 10}%
                                </span>
                              )}
                              {job.status === 'failed' && (
                                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1 shrink-0">
                                  <AlertCircle className="w-3 h-3" /> Falhou
                                </span>
                              )}
                            </div>

                            {/* PROCESSING PROGRESS BAR */}
                            {job.status === 'processing' && (
                              <div className="space-y-1.5 p-3 rounded-xl bg-slate-50 border border-slate-200">
                                <div className="flex justify-between text-[10px] text-slate-600 font-medium">
                                  <span>Renderizando com IA...</span>
                                  <span>{job.progress || 10}%</span>
                                </div>
                                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                                  <div
                                    className="bg-[#0066FF] h-full rounded-full transition-all duration-500"
                                    style={{ width: `${Math.max(job.progress || 10, 8)}%` }}
                                  />
                                </div>
                              </div>
                            )}

                            {/* 9:16 VERTICAL VIDEO PLAYER */}
                            {isReadyOrScheduled && (
                              <div className="relative rounded-xl overflow-hidden bg-black aspect-[9/16] max-h-[380px] w-full mx-auto border border-slate-200 shadow-inner flex items-center justify-center">
                                {job.output_path.startsWith('http') ? (
                                  <video
                                    src={videoSrc}
                                    controls
                                    className="w-full h-full object-cover"
                                  />
                                ) : (
                                  <div className="p-4 text-center space-y-2">
                                    <Play className="w-8 h-8 text-white/80 mx-auto" />
                                    <p className="text-xs text-slate-300">Vídeo gerado e pronto.</p>
                                  </div>
                                )}

                                {/* IA vs ORIGINAL COMPARISON TOGGLE */}
                                <div className="absolute top-2.5 right-2.5 bg-white/90 backdrop-blur-md rounded-lg p-1 border border-slate-200 flex text-[10px] shadow-md">
                                  <button
                                    onClick={() => setPlayerMode(p => ({ ...p, [job.id]: 'ia' }))}
                                    className={`px-2 py-1 rounded-md font-bold transition-all ${
                                      currentMode === 'ia' ? 'bg-[#0066FF] text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
                                    }`}
                                  >
                                    IA Clone
                                  </button>
                                  <button
                                    onClick={() => setPlayerMode(p => ({ ...p, [job.id]: 'original' }))}
                                    className={`px-2 py-1 rounded-md font-bold transition-all ${
                                      currentMode === 'original' ? 'bg-slate-200 text-slate-900' : 'text-slate-600 hover:text-slate-900'
                                    }`}
                                  >
                                    Original
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* ACTION BUTTONS (COMPLETED & SCHEDULED) */}
                          {isReadyOrScheduled && (
                            <div className="flex gap-2 pt-2 border-t border-slate-100">
                              <button
                                onClick={() => handlePublishNow(job.id)}
                                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white py-2.5 text-xs font-bold shadow-sm shadow-blue-600/20 transition-all"
                              >
                                <Send className="w-3.5 h-3.5" /> Postar Agora
                              </button>
                              {job.status === 'scheduled' && (
                                <button
                                  onClick={() => openEditScheduleModal(job)}
                                  className="inline-flex items-center justify-center gap-1 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-700 px-3 py-2.5 text-xs font-bold border border-amber-200 transition-all shrink-0"
                                  title="Editar ou Cancelar Agendamento"
                                >
                                  <Clock className="w-3.5 h-3.5 text-amber-600" />
                                  <span>Editar</span>
                                </button>
                              )}
                              {job.output_path && (
                                <a
                                  href={job.output_path.startsWith('http') ? job.output_path : `${API_BASE}/jobs/${job.id}/download`}
                                  download
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center justify-center gap-1 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 px-3.5 py-2.5 text-xs font-semibold border border-slate-200 transition-all"
                                  title="Baixar MP4"
                                >
                                  <Download className="w-4 h-4 text-slate-700" />
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: CALENDÁRIO & AGENDAMENTO EM LOTE */}
          {activeTab === 'calendar' && (
            <div className="space-y-8">
              
              {/* BATCH SCHEDULER TOOL */}
              <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-600" /> Agendamento em Lote de Reels
                  </h3>
                  <span className="text-xs text-[#0066FF] font-semibold">Distribuir postagens na fila</span>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed">
                  Selecione múltiplos vídeos prontos para enfileirar no Instagram com o intervalo automático configurado.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-700">Intervalo entre publicações</label>
                    <select
                      value={batchInterval}
                      onChange={(e) => setBatchInterval(Number(e.target.value))}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                    >
                      <option value={1}>A cada 1 hora</option>
                      <option value={2}>A cada 2 horas</option>
                      <option value={3}>A cada 3 horas (Recomendado)</option>
                      <option value={5}>A cada 5 horas</option>
                      <option value={8}>A cada 8 horas</option>
                      <option value={12}>A cada 12 horas</option>
                      <option value={24}>A cada 24 horas (1 por dia)</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-700">Vídeos prontos ({selectedJobIds.length} selecionados)</label>
                    <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                      {jobs.filter(j => j.status === 'completed').length === 0 ? (
                        <p className="text-[11px] text-slate-500 text-center py-4 bg-slate-50 rounded-xl border border-slate-200">
                          Nenhum Reels pronto disponível para agendamento.
                        </p>
                      ) : (
                        jobs.filter(j => j.status === 'completed').map((j) => (
                          <div
                            key={j.id}
                            onClick={() => toggleJobSelection(j.id)}
                            className={`p-3 rounded-xl border text-xs cursor-pointer flex items-center justify-between transition-all ${
                              selectedJobIds.includes(j.id)
                                ? 'border-amber-300 bg-amber-50 text-amber-900'
                                : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300'
                            }`}
                          >
                            <span className="truncate max-w-[280px] font-mono text-[11px]">{j.url}</span>
                            <input type="checkbox" checked={selectedJobIds.includes(j.id)} readOnly className="rounded accent-amber-600 w-4 h-4" />
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {batchMessage && (
                  <p className="text-xs text-amber-800 bg-amber-50 p-3 rounded-xl border border-amber-200">{batchMessage}</p>
                )}

                <button
                  onClick={handleBatchSchedule}
                  disabled={batchScheduling || selectedJobIds.length === 0}
                  className="w-full rounded-xl bg-amber-600 hover:bg-amber-700 text-white py-3 text-xs font-bold shadow-sm shadow-amber-600/20 disabled:opacity-50 transition-all"
                >
                  {batchScheduling ? 'Agendando...' : `Agendar ${selectedJobIds.length} Vídeo(s) na Fila`}
                </button>
              </div>

              {/* VISUAL SCHEDULED CALENDAR FEED */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Próximas Publicações Agendadas</h3>
                {jobs.filter(j => j.status === 'scheduled').length === 0 ? (
                  <div className="p-8 text-center border border-slate-200 rounded-2xl text-xs text-slate-500 bg-white">
                    Nenhum post agendado no momento.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {jobs.filter(j => j.status === 'scheduled').map((j) => {
                      const currentMode = playerMode[j.id] || 'ia'
                      const videoSrc = currentMode === 'ia' ? j.output_path : (j.original_s3_url || j.url)

                      return (
                        <div key={j.id} className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between">
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                                <Clock className="w-3 h-3" /> Agendado ({formatScheduledTime(j.scheduled_at)})
                              </span>
                            </div>
                            <p className="text-xs font-mono text-slate-600 truncate" title={j.url}>{j.url}</p>

                            {/* PLAYER 9:16 IN CALENDAR TAB */}
                            {j.output_path && (
                              <div className="relative rounded-xl overflow-hidden bg-black aspect-[9/16] max-h-[340px] w-full mx-auto border border-slate-200 flex items-center justify-center">
                                {j.output_path.startsWith('http') ? (
                                  <video src={videoSrc} controls className="w-full h-full object-cover" />
                                ) : (
                                  <div className="p-4 text-center space-y-2">
                                    <Play className="w-8 h-8 text-amber-500 mx-auto" />
                                    <p className="text-xs text-slate-300">Vídeo agendado pronto para prévia.</p>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>

                          {/* ACTION BUTTONS FOR SCHEDULED POSTS */}
                          <div className="flex gap-2 pt-2 border-t border-slate-100">
                            <button
                              onClick={() => handlePublishNow(j.id)}
                              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white py-2 text-xs font-bold shadow-sm shadow-blue-600/20 transition-all"
                            >
                              <Send className="w-3.5 h-3.5" /> Postar Agora
                            </button>
                            <button
                              onClick={() => openEditScheduleModal(j)}
                              className="inline-flex items-center justify-center gap-1 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-700 px-3 py-2 text-xs font-bold border border-amber-200 transition-all shrink-0"
                              title="Editar ou Cancelar Agendamento"
                            >
                              <Clock className="w-3.5 h-3.5 text-amber-600" />
                              <span>Editar</span>
                            </button>
                            {j.output_path && (
                              <a
                                href={j.output_path.startsWith('http') ? j.output_path : `${API_BASE}/jobs/${j.id}/download`}
                                download
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center justify-center gap-1 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 text-xs font-semibold border border-slate-200 transition-all"
                                title="Baixar Vídeo"
                              >
                                <Download className="w-4 h-4 text-slate-700" />
                              </a>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

            </div>
          )}

          {/* TAB 3: CONFIGURAÇÕES & AJUSTES */}
          {activeTab === 'editor' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* LEGENDA FIXA & REELS OPTIONS */}
              <form onSubmit={handleSaveSettings} className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5 shadow-sm hover:shadow-md transition-all">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                  <Settings className="w-4 h-4 text-[#0066FF]" /> Configurações de Postagem Automática
                </h3>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-700">Legenda Fixa Padrão (Assinatura)</label>
                  <textarea
                    rows={3}
                    value={defaultCaptionSuffix}
                    onChange={(e) => setDefaultCaptionSuffix(e.target.value)}
                    placeholder="Ex: Siga @seu_perfil para mais conteúdos como esse! #reels #viral"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-900 placeholder-slate-400 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                  />
                  <p className="text-[10px] text-slate-500">Esta assinatura será anexada no final da legenda do Reels clonado.</p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-700">Intervalo de Agendamento Padrão</label>
                  <select
                    value={intervalHours}
                    onChange={(e) => setIntervalHours(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                  >
                    <option value={0}>Postagem Imediata (Assim que o Reels ficar pronto)</option>
                    <option value={1}>A cada 1 hora</option>
                    <option value={2}>A cada 2 horas</option>
                    <option value={3}>A cada 3 horas (Recomendado)</option>
                    <option value={5}>A cada 5 horas</option>
                    <option value={8}>A cada 8 horas</option>
                    <option value={12}>A cada 12 horas</option>
                    <option value={24}>A cada 24 horas (1 por dia)</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50">
                  <div>
                    <p className="text-xs font-semibold text-slate-900">Postar Apenas na Aba Reels</p>
                    <p className="text-[10px] text-slate-500">Não compartilha o vídeo na grade do Feed principal</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={!shareToFeed}
                    onChange={(e) => setShareToFeed(!e.target.checked)}
                    className="w-4 h-4 rounded accent-[#0066FF]"
                  />
                </div>

                {/* META INSTAGRAM CONNECT */}
                <div className="space-y-3 pt-3 border-t border-slate-100">
                  <label className="text-xs font-semibold text-slate-700">Conexão Meta / Instagram Graph API</label>
                  <a
                    href="/api/v1/auth/instagram/login"
                    className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-slate-900 hover:bg-slate-800 text-white py-3 text-xs font-bold shadow-sm transition-all"
                  >
                    <Sparkles className="w-4 h-4 text-[#0066FF]" /> Logar Direto com o Instagram Meta
                  </a>

                  <div className="space-y-2 pt-2">
                    <input
                      type="text"
                      value={igAccountId}
                      onChange={(e) => setIgAccountId(e.target.value)}
                      placeholder="Instagram Account ID"
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
                    />
                    <input
                      type="password"
                      value={igAccessToken}
                      onChange={(e) => setIgAccessToken(e.target.value)}
                      placeholder="Access Token (Meta Token)"
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none"
                    />
                  </div>
                </div>

                {settingsMessage && (
                  <p className="text-xs text-blue-800 bg-blue-50 p-3 rounded-xl border border-blue-200">{settingsMessage}</p>
                )}

                <button
                  type="submit"
                  disabled={settingsSaving}
                  className="w-full rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white py-3 text-xs font-bold shadow-sm shadow-blue-600/20 transition-all"
                >
                  {settingsSaving ? 'Salvando...' : 'Salvar Preferências'}
                </button>
              </form>

              {/* SECOND COLUMN: COOKIES & SHORTCUT */}
              <div className="space-y-6">
                {/* INSTAGRAM COOKIES CARD */}
                <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-sm hover:shadow-md transition-all">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 flex items-center gap-2">
                        <FileVideo className="w-4 h-4 text-amber-600" /> Cookies do Instagram (yt-dlp)
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-1">Envie o arquivo <code className="text-amber-800 font-mono font-bold">cookies.txt</code> para baixar Reels protegidos.</p>
                    </div>
                    {cookieStatus === 'active' ? (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Ativo
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        Ausente
                      </span>
                    )}
                  </div>

                  {cookieMessage && (
                    <p className="text-xs text-amber-800 bg-amber-50 p-3 rounded-xl border border-amber-200">{cookieMessage}</p>
                  )}

                  <label className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 py-3 text-xs font-bold border border-slate-200 cursor-pointer transition-all">
                    <Upload className="w-4 h-4 text-slate-700" />
                    <span>{cookieUploading ? 'Enviando...' : 'Carregar cookies.txt'}</span>
                    <input type="file" accept=".txt" onChange={handleCookiesUpload} disabled={cookieUploading} className="hidden" />
                  </label>
                </div>

                {/* IOS SHORTCUT CONNECT CARD */}
                <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-sm hover:shadow-md transition-all">
                  <div className="flex items-center gap-2 text-[#0066FF] font-bold text-xs">
                    <Smartphone className="w-4 h-4" /> Atalho do iPhone (iOS Shortcut)
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">Chave de API única para configurar a automação direta no menu de compartilhamento do iOS:</p>
                  <div className="flex items-center gap-2">
                    <input type="text" readOnly value={apiKey} className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs font-mono text-slate-800 focus:outline-none" />
                    <button onClick={handleCopyKey} className="rounded-xl bg-blue-50 hover:bg-blue-100 text-[#0066FF] px-4 py-2.5 text-xs font-bold border border-blue-200 transition-all">
                      {copied ? 'Copiado!' : 'Copiar'}
                    </button>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB 4: BIBLIOTECA DE VÍDEOS */}
          {activeTab === 'library' && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Video className="w-4 h-4 text-[#0066FF]" /> Sua Biblioteca de Vídeos
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">Vídeos locais que o motor de IA selecionará para mesclar e criar seus Reels.</p>
                  </div>
                  
                  <label className="rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white px-4 py-2.5 text-xs font-bold cursor-pointer shadow-sm shadow-blue-600/20 shrink-0 inline-flex items-center gap-1.5 transition-all">
                    <Upload className="w-4 h-4" /> Upload em Lote (Até 30 vídeos)
                    <input type="file" multiple accept=".mp4,.mov" onChange={handleFileUpload} disabled={uploading} className="hidden" />
                  </label>
                </div>

                {uploadMessage && (
                  <p className="text-xs text-blue-800 bg-blue-50 p-3 rounded-xl border border-blue-200">{uploadMessage}</p>
                )}

                {videos.length === 0 ? (
                  <div className="border border-dashed border-slate-200 rounded-2xl p-12 text-center space-y-2 bg-slate-50">
                    <FileVideo className="w-10 h-10 text-slate-300 mx-auto" />
                    <p className="text-xs text-slate-500">Sua biblioteca está vazia. Faça o upload de vídeos MP4/MOV acima!</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {videos.map((vid) => (
                      <div key={vid.id || vid.path} className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 flex items-center justify-between gap-3 hover:bg-white hover:border-slate-300 transition-all">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-[#0066FF] shrink-0">
                            <Video className="w-5 h-5" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-slate-800 truncate">{vid.filename}</p>
                            <p className="text-[10px] text-slate-500 truncate">{vid.description || 'Indexado pela IA'}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteVideo(vid.id)}
                          className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-slate-100 transition-all shrink-0"
                          title="Remover Vídeo"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: GESTÃO DE USUÁRIOS (ADMIN) */}
          {activeTab === 'users' && isAdmin && (
            <UserManagementTab apiKey={apiKey} />
          )}

        </div>
      </main>

      {/* MOBILE BOTTOM NAVIGATION BAR (FIXED LIGHT STYLE) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-lg border-t border-slate-200 px-4 py-2 shadow-lg">
        <div className="max-w-md mx-auto flex items-center justify-between text-center">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <button
                key={item.id}
                onClick={() => changeTab(item.id as any)}
                className={`flex flex-col items-center gap-1 transition-all ${
                  isActive ? 'text-[#0066FF] font-bold scale-105' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-[10px]">{item.label}</span>
              </button>
            )
          })}
        </div>
      </nav>

      {/* EDIT SCHEDULE MODAL POPUP */}
      {editingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600" /> Editar Agendamento
              </h3>
              <button
                onClick={() => setEditingJob(null)}
                className="px-2 py-1 text-xs font-bold text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-all"
              >
                X
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-mono text-slate-600 truncate">{editingJob.url}</p>

              {editingJob.output_path && (
                <div className="relative rounded-xl overflow-hidden bg-black aspect-[9/16] max-h-[220px] w-full mx-auto border border-slate-200 flex items-center justify-center">
                  <video src={editingJob.output_path} controls className="w-full h-full object-cover" />
                </div>
              )}

              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-slate-700">Nova Data e Horário de Publicação</label>
                <input
                  type="datetime-local"
                  value={newScheduleTime}
                  onChange={(e) => setNewScheduleTime(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-900 focus:border-[#0066FF] focus:bg-white focus:outline-none transition-all"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={handleUpdateScheduleTime}
                disabled={savingSchedule || !newScheduleTime}
                className="w-full rounded-xl bg-[#0066FF] hover:bg-blue-700 text-white py-2.5 text-xs font-bold shadow-sm shadow-blue-600/20 disabled:opacity-50 transition-all"
              >
                {savingSchedule ? 'Salvando...' : 'Salvar Novo Horário'}
              </button>

              <button
                onClick={handleCancelSchedule}
                disabled={savingSchedule}
                className="w-full rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 py-2.5 text-xs font-bold disabled:opacity-50 transition-all flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                <span>Cancelar Agendamento</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}