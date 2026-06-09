import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ShieldCheck, Copy, CheckCircle, AlertTriangle, Eye, EyeOff, ArrowRight, RefreshCw } from 'lucide-react'
import { setApiKey } from '../api'

interface RevealData {
  api_key: string
  user_email: string
  user_name: string
  user_picture: string
  is_new_user: boolean
}

interface Props {
  revealToken: string
  onDone: () => void
}

export default function ApiKeyReveal({ revealToken, onDone }: Props) {
  const [data, setData]         = useState<RevealData | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [copied, setCopied]     = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [visible, setVisible]   = useState(false)

  useEffect(() => {
    fetch(`/api/auth/reveal?token=${encodeURIComponent(revealToken)}`)
      .then(r => {
        if (r.status === 410) throw new Error('Link expired or already used. Please sign in again.')
        if (!r.ok) throw new Error('Failed to retrieve API key.')
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [revealToken])

  const handleCopy = () => {
    if (!data) return
    navigator.clipboard.writeText(data.api_key).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    })
  }

  const handleEnterDashboard = () => {
    if (!data || !confirmed) return
    setApiKey(data.api_key)
    // Clean URL params
    window.history.replaceState({}, '', window.location.pathname)
    onDone()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-sm">Retrieving your API key…</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Link Expired</h2>
          <p className="text-sm text-gray-500 mb-6">{error}</p>
          <a href="/api/auth/google"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors">
            Sign in again
          </a>
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-teal-500/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden"
      >
        {/* Top banner */}
        <div className={`px-8 py-5 ${data.is_new_user ? 'bg-teal-600' : 'bg-amber-500'}`}>
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-6 h-6 text-white" />
            <div>
              <p className="text-white font-bold text-base">
                {data.is_new_user ? 'Welcome to HonestLedger!' : 'New API key generated'}
              </p>
              <p className="text-white/80 text-xs mt-0.5">
                {data.is_new_user
                  ? 'Your account has been created successfully.'
                  : 'Your previous key has been revoked. Here is your new key.'}
              </p>
            </div>
          </div>
        </div>

        <div className="px-8 py-6 space-y-5">
          {/* User info */}
          <div className="flex items-center gap-3">
            {data.user_picture ? (
              <img src={data.user_picture} alt="" className="w-10 h-10 rounded-full" />
            ) : (
              <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                <span className="text-teal-700 font-bold text-sm">{(data.user_name || 'U')[0].toUpperCase()}</span>
              </div>
            )}
            <div>
              <p className="font-semibold text-gray-900 text-sm">{data.user_name}</p>
              <p className="text-xs text-gray-500">{data.user_email}</p>
            </div>
          </div>

          {/* Critical warning */}
          <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-4">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-bold text-red-700">This key will NEVER be shown again</p>
                <p className="text-xs text-red-600 mt-1 leading-relaxed">
                  Copy it now and store it in a password manager or a secure location.
                  Once you leave this page, this key cannot be recovered — you would need to sign in again to generate a new one.
                </p>
              </div>
            </div>
          </div>

          {/* API Key display */}
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2 block">Your API Key</label>
            <div className="flex items-center gap-2 bg-slate-900 rounded-xl px-4 py-3 font-mono">
              <span className="flex-1 text-sm text-green-400 break-all select-all">
                {visible ? data.api_key : data.api_key.slice(0, 6) + '•'.repeat(data.api_key.length - 10) + data.api_key.slice(-4)}
              </span>
              <button onClick={() => setVisible(v => !v)}
                className="p-1.5 text-slate-400 hover:text-white transition-colors">
                {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
              <button onClick={handleCopy}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${copied ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'}`}>
                {copied ? <><CheckCircle className="w-3.5 h-3.5" /> Copied!</> : <><Copy className="w-3.5 h-3.5" /> Copy</>}
              </button>
            </div>
          </div>

          {/* Confirmation checkbox */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <div className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${confirmed ? 'bg-teal-600 border-teal-600' : 'border-gray-300 group-hover:border-teal-400'}`}
              onClick={() => setConfirmed(c => !c)}>
              {confirmed && <CheckCircle className="w-3 h-3 text-white" />}
            </div>
            <span className="text-sm text-gray-600 leading-relaxed">
              I have copied and stored my API key in a safe location. I understand it cannot be shown again.
            </span>
          </label>

          {/* CTA */}
          <button
            onClick={handleEnterDashboard}
            disabled={!confirmed || !copied}
            className="w-full flex items-center justify-center gap-2 py-3.5 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-100 disabled:text-gray-400 text-white font-semibold rounded-xl transition-all text-sm"
          >
            Enter Dashboard <ArrowRight className="w-4 h-4" />
          </button>
          {!copied && (
            <p className="text-xs text-center text-gray-400">Copy your key first to continue</p>
          )}
        </div>
      </motion.div>
    </div>
  )
}
