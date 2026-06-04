import { motion } from 'framer-motion'
import { Play, Brain, Shield, AlertTriangle, RefreshCw, Loader2, Zap } from 'lucide-react'
import type { AppStatus } from '../types'

interface Props {
  status: AppStatus | null
  hasReconcile: boolean
  hasProposal: boolean
  onReconcile: () => void
  onJudge: () => void
  onVerify: () => void
  onVerifyGreedy: () => void
  onSeedDemo: () => void
  onReset: () => void
  loading: string | null
}

interface BtnProps {
  label: string
  icon: React.ReactNode
  onClick: () => void
  loading?: boolean
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
}

function ActionButton({ label, icon, onClick, loading, disabled, variant = 'secondary' }: BtnProps) {
  const base = 'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all'
  const styles = {
    primary: 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm',
    secondary: 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50',
    danger: 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100',
    ghost: 'text-gray-400 hover:text-gray-600 hover:bg-gray-50',
  }

  return (
    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
      onClick={onClick} disabled={disabled || loading}
      className={`${base} ${styles[variant]} ${(disabled || loading) ? 'opacity-50 cursor-not-allowed' : ''}`}>
      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : icon}
      {label}
    </motion.button>
  )
}

export function ActionBar({ status, hasReconcile, hasProposal, onReconcile, onJudge, onVerify, onVerifyGreedy, onSeedDemo, onReset, loading }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-5 py-3 space-y-2">
      <div className="flex items-center justify-between gap-4">
        {/* Live pipeline buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <ActionButton label="Run Reconcile" icon={<Play className="w-3.5 h-3.5" />}
            onClick={onReconcile} loading={loading === 'reconcile'} variant="primary" />

          <ActionButton label="Run Judge" icon={<Brain className="w-3.5 h-3.5" />}
            onClick={onJudge} loading={loading === 'judge'}
            disabled={!hasReconcile} />

          <ActionButton label="Verify Proposal" icon={<Shield className="w-3.5 h-3.5" />}
            onClick={onVerify} loading={loading === 'verify'}
            disabled={!hasProposal} />

          <ActionButton label="Greedy Attack" icon={<AlertTriangle className="w-3.5 h-3.5" />}
            onClick={onVerifyGreedy} loading={loading === 'greedy'}
            variant="danger" />
        </div>

        <div className="flex items-center gap-2">
          {status && (
            <div className="text-xs text-gray-500 font-mono hidden sm:block">
              rules: <span className="text-teal-600 font-medium">{status.current_rule_version}</span>
            </div>
          )}
          <ActionButton label="Reset" icon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={onReset} variant="ghost" />
        </div>
      </div>

      {/* Demo mode row */}
      <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
        <span className="text-xs text-gray-400 font-medium">Demo mode:</span>
        <ActionButton label="⚡ Seed Full Demo (instant)" icon={<Zap className="w-3.5 h-3.5" />}
          onClick={onSeedDemo} loading={loading === 'seed'}
          variant="secondary" />
        <span className="text-xs text-gray-300">Loads pre-computed results — no Gemini calls, perfect for recording</span>
      </div>

      <div className="flex items-center gap-3">
        {status && (
          <div className="text-xs text-gray-500 font-mono hidden sm:block">
            rules: <span className="text-teal-600 font-medium">{status.current_rule_version}</span>
          </div>
        )}
        <ActionButton label="Reset" icon={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={onReset} variant="ghost" />
      </div>
    </div>
  )
}
