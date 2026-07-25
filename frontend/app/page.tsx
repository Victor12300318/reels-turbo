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
  Lock
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

    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }

    fetchInitialData(key)

    // Smart Adaptive Polling: 6s when active jobs are running, 30s when idle
    const hasActiveJobs = jobs.some(j => j.status === 'processing' || j.status === 'pending' || j.status === 'downloading')
    const pollIntervalMs = hasActiveJobs ? 6000 : 30000

    const interval = setInterval(() => {
      fetchJobs(key)
    }, pollIntervalMs)

    return () => clearInterval(interval)
  }, [router, jobs.map(j => j.status).join(',')])

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

        // Derive job metrics locally to avoid extra HTTP calls
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
      new Notification('🎬 Reels Clonado com Sucesso!', {
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
        alert('🚀 Reels publicado no Instagram com sucesso!')
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
      setUploadMessage(`✅ ${successCount} de ${total} vídeo(s) enviado(s) para o S3 com sucesso!`)
      await fetchVideos(apiKey)
    } else {
      setUploadMessage('❌ Falha ao enviar os vídeos para o S3. Tente novamente.')
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
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 pb-24 font-sans antialiased">
      
      {/* MOBILE TOP HEADER */}
      <header className="sticky top-0 z-30 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white leading-tight">Reels Cloner AI</h1>
            <p className="text-[10px] text-slate-400 truncate max-w-[160px]">{userEmail}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-white rounded-lg">
          <LogOut className="w-4 h-4" />
        </button>
      </header>

      {/* MAIN MOBILE CONTAINER */}
      <main className="max-w-md mx-auto p-4 space-y-6">

        {/* METRICS SUMMARY BAR */}
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5">
            <p className="text-lg font-bold text-indigo-400">{metrics.total_cloned}</p>
            <p className="text-[9px] text-slate-400 uppercase font-medium">Clonados</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5">
            <p className="text-lg font-bold text-emerald-400">{metrics.total_published}</p>
            <p className="text-[9px] text-slate-400 uppercase font-medium">Postados</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5">
            <p className="text-lg font-bold text-amber-400">{metrics.scheduled_count}</p>
            <p className="text-[9px] text-slate-400 uppercase font-medium">Agendados</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5">
            <p className="text-lg font-bold text-pink-400">{metrics.library_count}</p>
            <p className="text-[9px] text-slate-400 uppercase font-medium">Biblioteca</p>
          </div>
        </div>

        {/* TAB 1: ⚡ CLONADOR (HOME FEED) */}
        {activeTab === 'cloner' && (
          <div className="space-y-6">
            
            {/* MANUAL URL INPUT */}
            <form onSubmit={handleCreateClone} className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-xl">
              <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-indigo-400" /> Clonar Link do Instagram
              </label>
              <div className="flex gap-2">
                <input
                  type="url"
                  required
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  placeholder="https://www.instagram.com/reel/..."
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={cloningNow}
                  className="rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 text-xs font-semibold shrink-0 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                >
                  {cloningNow ? 'Iniciando...' : 'Clonar'}
                </button>
              </div>
            </form>

            {/* JOBS FEED - VERTICAL CARDS (9:16) */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Seus Reels Processados</h2>
                <button onClick={() => fetchJobs(apiKey)} className="text-[11px] text-indigo-400 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" /> Atualizar
                </button>
              </div>

              {jobs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-800 p-8 text-center space-y-2">
                  <Sparkles className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs text-slate-400">Nenhum Reels clonado ainda.</p>
                  <p className="text-[10px] text-slate-500">Cole um link acima ou use o Atalho do iPhone!</p>
                </div>
              ) : (
                jobs.map((job) => {
                  const currentMode = playerMode[job.id] || 'ia'
                  const videoSrc = currentMode === 'ia' ? job.output_path : (job.original_s3_url || job.url)

                  return (
                    <div key={job.id} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 space-y-3 shadow-xl">
                      {/* CARD STATUS BADGE */}
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono text-indigo-300 truncate max-w-[180px]">
                          {job.url}
                        </span>
                        {job.status === 'completed' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Pronto
                          </span>
                        )}
                        {job.status === 'scheduled' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Agendado
                          </span>
                        )}
                        {job.status === 'processing' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse flex items-center gap-1">
                            <RefreshCw className="w-3 h-3 animate-spin" /> {job.progress || 10}%
                          </span>
                        )}
                        {job.status === 'failed' && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Falhou
                          </span>
                        )}
                      </div>

                      {/* PROCESSING PROGRESS BAR */}
                      {job.status === 'processing' && (
                        <div className="space-y-1.5 p-3 rounded-xl bg-slate-950 border border-indigo-500/20">
                          <div className="flex justify-between text-[10px] text-indigo-300 font-medium">
                            <span>Processando vídeo pela IA...</span>
                            <span>{job.progress || 10}%</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-indigo-500 via-pink-500 to-amber-400 h-full rounded-full transition-all duration-500"
                              style={{ width: `${Math.max(job.progress || 10, 8)}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* 9:16 VERTICAL VIDEO PLAYER */}
                      {job.status === 'completed' && job.output_path && (
                        <div className="relative rounded-xl overflow-hidden bg-black aspect-[9/16] max-h-[380px] mx-auto border border-slate-800 flex items-center justify-center">
                          {job.output_path.startsWith('http') ? (
                            <video
                              src={videoSrc}
                              controls
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="p-4 text-center space-y-2">
                              <Play className="w-8 h-8 text-indigo-400 mx-auto" />
                              <p className="text-xs text-slate-300">Vídeo pronto para download e envio.</p>
                            </div>
                          )}

                          {/* IA vs ORIGINAL COMPARISON TOGGLE */}
                          <div className="absolute top-2 right-2 bg-slate-900/90 backdrop-blur-md rounded-lg p-1 border border-slate-700/60 flex text-[10px]">
                            <button
                              onClick={() => setPlayerMode(p => ({ ...p, [job.id]: 'ia' }))}
                              className={`px-2 py-1 rounded-md font-semibold transition-all ${currentMode === 'ia' ? 'bg-indigo-600 text-white' : 'text-slate-400'}`}
                            >
                              IA Clone
                            </button>
                            <button
                              onClick={() => setPlayerMode(p => ({ ...p, [job.id]: 'original' }))}
                              className={`px-2 py-1 rounded-md font-semibold transition-all ${currentMode === 'original' ? 'bg-slate-700 text-white' : 'text-slate-400'}`}
                            >
                              Original
                            </button>
                          </div>
                        </div>
                      )}

                      {/* ACTION BUTTONS */}
                      {job.status === 'completed' && (
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={() => handlePublishNow(job.id)}
                            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-pink-600 hover:bg-pink-500 text-white py-2 text-xs font-semibold shadow-lg shadow-pink-600/20 transition-all"
                          >
                            <Send className="w-3.5 h-3.5" /> Postar Agora
                          </button>
                          {job.output_path && (
                            <a
                              href={job.output_path.startsWith('http') ? job.output_path : `${API_BASE}/jobs/${job.id}/download`}
                              download
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center justify-center gap-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 text-xs font-medium border border-slate-700"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        )}

        {/* TAB 2: 📅 CALENDÁRIO & AGENDAMENTO EM LOTE */}
        {activeTab === 'calendar' && (
          <div className="space-y-6">
            
            {/* BATCH SCHEDULER TOOL */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-4 shadow-xl">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" /> Agendamento em Lote
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Selecione os vídeos prontos para distribuir a postagem automática no intervalo configurado.
              </p>

              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-300">Intervalo de postagem</label>
                <select
                  value={batchInterval}
                  onChange={(e) => setBatchInterval(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value={1}>A cada 1 hora</option>
                  <option value={2}>A cada 2 horas</option>
                  <option value={3}>A cada 3 horas (Recomendado)</option>
                  <option value={6}>A cada 6 horas</option>
                  <option value={12}>A cada 12 horas</option>
                  <option value={24}>A cada 24 horas (1 por dia)</option>
                </select>
              </div>

              {/* UNPOSTED JOBS SELECTION LIST */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-300">Vídeos disponíveis para agendar ({selectedJobIds.length} selecionados)</label>
                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                  {jobs.filter(j => j.status === 'completed').length === 0 ? (
                    <p className="text-[11px] text-slate-500 text-center py-4">Nenhum Reels pronto disponível para agendamento.</p>
                  ) : (
                    jobs.filter(j => j.status === 'completed').map((j) => (
                      <div
                        key={j.id}
                        onClick={() => toggleJobSelection(j.id)}
                        className={`p-2.5 rounded-xl border text-xs cursor-pointer flex items-center justify-between transition-all ${selectedJobIds.includes(j.id) ? 'border-amber-500/50 bg-amber-500/10 text-amber-200' : 'border-slate-800 bg-slate-950 text-slate-400'}`}
                      >
                        <span className="truncate max-w-[220px] font-mono text-[11px]">{j.url}</span>
                        <input type="checkbox" checked={selectedJobIds.includes(j.id)} readOnly className="rounded accent-amber-500" />
                      </div>
                    ))
                  )}
                </div>
              </div>

              {batchMessage && (
                <p className="text-xs text-amber-400 bg-amber-950/40 p-2.5 rounded-xl border border-amber-500/20">{batchMessage}</p>
              )}

              <button
                onClick={handleBatchSchedule}
                disabled={batchScheduling || selectedJobIds.length === 0}
                className="w-full rounded-xl bg-amber-600 hover:bg-amber-500 text-white py-2.5 text-xs font-semibold shadow-lg shadow-amber-600/20 disabled:opacity-50 transition-all"
              >
                {batchScheduling ? 'Agendando...' : `Agendar ${selectedJobIds.length} Vídeo(s)`}
              </button>
            </div>

            {/* VISUAL SCHEDULED CALENDAR FEED */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Próximas Publicações Agendadas</h3>
              {jobs.filter(j => j.status === 'scheduled').length === 0 ? (
                <div className="p-6 text-center border border-slate-800 rounded-2xl text-xs text-slate-500">
                  Nenhum post agendado no momento.
                </div>
              ) : (
                jobs.filter(j => j.status === 'scheduled').map((j) => (
                  <div key={j.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-white flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-amber-400" />
                        {j.scheduled_at ? new Date(j.scheduled_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : 'Em breve'}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate max-w-[200px] mt-0.5">{j.url}</p>
                    </div>
                    <span className="px-2 py-0.5 rounded-md text-[10px] bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30">
                      Agendado
                    </span>
                  </div>
                ))
              )}
            </div>

          </div>
        )}

        {/* TAB 3: ✍️ EDITOR & CONFIGURAÇÕES */}
        {activeTab === 'editor' && (
          <div className="space-y-6">
            
            {/* LEGENDA FIXA & REELS OPTIONS */}
            <form onSubmit={handleSaveSettings} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-4 shadow-xl">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-400" /> Configurações de Postagem
              </h2>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Legenda Fixa Padrão (Assinatura)</label>
                <textarea
                  rows={3}
                  value={defaultCaptionSuffix}
                  onChange={(e) => setDefaultCaptionSuffix(e.target.value)}
                  placeholder="Ex: Siga @agufzz para mais conteúdos como esse! #reels #viral"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
                <p className="text-[10px] text-slate-500">Esta assinatura é anexada automaticamente no final do texto do Reels.</p>
              </div>

              {/* POST EXCLUSIVELY TO REELS TOGGLE */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950">
                <div>
                  <p className="text-xs font-medium text-white">Postar Apenas no Reels</p>
                  <p className="text-[10px] text-slate-400">Não compartilha o vídeo na grade do Feed principal</p>
                </div>
                <input
                  type="checkbox"
                  checked={!shareToFeed}
                  onChange={(e) => setShareToFeed(!e.target.checked)}
                  className="w-4 h-4 rounded accent-indigo-600"
                />
              </div>

              {/* META INSTAGRAM CONNECT */}
              <div className="space-y-3 pt-2 border-t border-slate-800">
                <label className="text-xs font-medium text-slate-300">Conexão Meta / Instagram Graph API</label>
                <a
                  href="/api/v1/auth/instagram/login"
                  className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-purple-600 via-pink-600 to-amber-500 hover:opacity-90 text-white py-2.5 text-xs font-semibold shadow-lg shadow-pink-600/20 transition-all"
                >
                  <Sparkles className="w-4 h-4" /> Logar Direto com o Instagram
                </a>

                <div className="space-y-2 pt-2">
                  <input
                    type="text"
                    value={igAccountId}
                    onChange={(e) => setIgAccountId(e.target.value)}
                    placeholder="Instagram Account ID (37861...)"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                  <input
                    type="password"
                    value={igAccessToken}
                    onChange={(e) => setIgAccessToken(e.target.value)}
                    placeholder="Access Token (IGAAM...)"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              {settingsMessage && (
                <p className="text-xs text-indigo-400 bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/20">{settingsMessage}</p>
              )}

              <button
                type="submit"
                disabled={settingsSaving}
                className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all"
              >
                {settingsSaving ? 'Salvando...' : 'Salvar Preferências'}
              </button>
            </form>

            {/* INSTAGRAM COOKIES CARD (yt-dlp) */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-3 shadow-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                    <FileVideo className="w-4 h-4 text-amber-400" /> Cookies do Instagram (yt-dlp)
                  </h3>
                  <p className="text-[11px] text-slate-400">Envie o arquivo <code className="text-amber-300">cookies.txt</code> para baixar Reels protegidos.</p>
                </div>
                {cookieStatus === 'active' ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Ativo
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    Ausente
                  </span>
                )}
              </div>

              {cookieMessage && (
                <p className="text-xs text-amber-400 bg-amber-950/40 p-2.5 rounded-xl border border-amber-500/20">{cookieMessage}</p>
              )}

              <label className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 py-2.5 text-xs font-semibold border border-slate-700 cursor-pointer transition-all">
                <Upload className="w-4 h-4 text-amber-400" />
                <span>{cookieUploading ? 'Enviando...' : 'Carregar cookies.txt'}</span>
                <input type="file" accept=".txt" onChange={handleCookiesUpload} disabled={cookieUploading} className="hidden" />
              </label>
            </div>

            {/* IOS SHORTCUT CONNECT CARD */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-3 shadow-xl">
              <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs">
                <Smartphone className="w-4 h-4" /> Atalho do iPhone (iOS Shortcut)
              </div>
              <p className="text-[11px] text-slate-400">Chave de API única para configurar no Share Sheet do iOS:</p>
              <div className="flex items-center gap-2">
                <input type="text" readOnly value={apiKey} className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-mono text-indigo-300 focus:outline-none" />
                <button onClick={handleCopyKey} className="rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 px-3 py-2 text-xs font-medium border border-indigo-500/30">
                  {copied ? 'Copiado!' : 'Copiar'}
                </button>
              </div>
            </div>

          </div>
        )}

        {/* TAB 4: 📁 BIBLIOTECA DE VÍDEOS */}
        {activeTab === 'library' && (
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Video className="w-4 h-4 text-indigo-400" /> Seus Vídeos Locais
                  </h2>
                  <p className="text-xs text-slate-400">Vídeos cadastrados que a IA usará como fonte.</p>
                </div>
                
                <label className="rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold cursor-pointer shadow-md shadow-indigo-600/20">
                  + Upload em Lote (Até 30)
                  <input type="file" multiple accept=".mp4,.mov" onChange={handleFileUpload} disabled={uploading} className="hidden" />
                </label>
              </div>

              {uploadMessage && (
                <p className="text-xs text-indigo-400 bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/20">{uploadMessage}</p>
              )}

              {videos.length === 0 ? (
                <div className="border border-dashed border-slate-800 rounded-xl p-8 text-center space-y-2">
                  <FileVideo className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs text-slate-400">Sua biblioteca está vazia.</p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {videos.map((vid) => (
                    <div key={vid.id || vid.path} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-9 h-9 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                          <Video className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-slate-200 truncate">{vid.filename}</p>
                          <p className="text-[10px] text-slate-500 truncate">{vid.description || 'Indexado e pronto'}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteVideo(vid.id)}
                        className="p-2 text-slate-500 hover:text-rose-400 rounded-lg shrink-0"
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

        {/* TAB 5: 👥 GESTÃO DE USUÁRIOS (ADMIN) */}
        {activeTab === 'users' && isAdmin && (
          <UserManagementTab apiKey={apiKey} />
        )}

      </main>

      {/* MOBILE BOTTOM NAVIGATION BAR (FIXED) */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-[#090d16]/95 backdrop-blur-lg border-t border-slate-800/80 px-6 py-2">
        <div className="max-w-md mx-auto flex items-center justify-between text-center">
          
          <button
            onClick={() => setActiveTab('cloner')}
            className={`flex flex-col items-center gap-1 transition-all ${activeTab === 'cloner' ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Zap className="w-5 h-5" />
            <span className="text-[10px] font-medium">Clonador</span>
          </button>

          <button
            onClick={() => setActiveTab('calendar')}
            className={`flex flex-col items-center gap-1 transition-all ${activeTab === 'calendar' ? 'text-amber-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <CalendarIcon className="w-5 h-5" />
            <span className="text-[10px] font-medium">Agenda</span>
          </button>

          <button
            onClick={() => setActiveTab('editor')}
            className={`flex flex-col items-center gap-1 transition-all ${activeTab === 'editor' ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Settings className="w-5 h-5" />
            <span className="text-[10px] font-medium">Ajustes</span>
          </button>

          <button
            onClick={() => setActiveTab('library')}
            className={`flex flex-col items-center gap-1 transition-all ${activeTab === 'library' ? 'text-pink-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Video className="w-5 h-5" />
            <span className="text-[10px] font-medium">Biblioteca</span>
          </button>

          {isAdmin && (
            <button
              onClick={() => setActiveTab('users')}
              className={`flex flex-col items-center gap-1 transition-all ${activeTab === 'users' ? 'text-amber-400' : 'text-slate-500 hover:text-slate-300'}`}
            >
              <Users className="w-5 h-5" />
              <span className="text-[10px] font-medium">Usuários</span>
            </button>
          )}

        </div>
      </nav>

    </div>
  )
}
