import { useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, Copy, CheckCircle, AlertTriangle, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { setApiKey } from '../api'

interface Props {
  apiKey: string
  userName: string
  userEmail: string
  onDone: () => void
}

export default function ApiKeyReveal({ apiKey, userName, userEmail, onDone }: Props) {
  const [copied, setCopied]       = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [visible, setVisible]     = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    })
  }

  const handleEnterDashboard = () => {
    if (!confirmed) return
    setApiKey(apiKey)
    onDone()
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-teal-500/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden"
      >
        {/* Top banner */}
        <div className="px-8 py-5 bg-teal-600">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-6 h-6 text-white" />
            <div>
              <p className="text-white font-bold text-base">Welcome to HonestLedger!</p>
              <p className="text-white/80 text-xs mt-0.5">Your account has been created successfully.</p>
            </div>
          </div>
        </div>

        <div className="px-8 py-6 space-y-5">
          {/* User info */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
              <span className="text-teal-700 font-bold text-sm">{(userName || 'U')[0].toUpperCase()}</span>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">{userName}</p>
              <p className="text-xs text-gray-500">{userEmail}</p>
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
                  Once you leave this page, this key cannot be recovered.
                </p>
              </div>
            </div>
          </div>

          {/* API Key display */}
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2 block">Your API Key</label>
            <div className="flex items-center gap-2 bg-slate-900 rounded-xl px-4 py-3 font-mono">
              <span className="flex-1 text-sm text-green-400 break-all select-all">
                {visible ? apiKey : apiKey.slice(0, 6) + '•'.repeat(apiKey.length - 10) + apiKey.slice(-4)}
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
            <div
              className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${confirmed ? 'bg-teal-600 border-teal-600' : 'border-gray-300 group-hover:border-teal-400'}`}
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
