import { motion } from 'framer-motion'
import {
  Play, Brain, Shield, AlertTriangle, RefreshCw,
  Loader2, Zap, ChevronRight, CheckCircle2, XCircle,
} from 'lucide-react'
import type { AppStatus } from '../types'

interface Props {
  status: AppStatus | null
  hasReconcile: boolean
  hasProposal: boolean
  isOptimal: boolean
  verifyVerdict?: string | null
  hasUpload: boolean
  onReconcile: () => void
  onJudge: () => void
  onVerify: () => void
  onVerifyGreedy: () => void
  onApprove?: () => void
  onReject?: () => void
  onSeedDemo: () => void
  onReset: () => void
  loading: string | null
  pipelineRunning: boolean
}

interface PrimaryCTA {
  label: string
  sublabel: string
  icon: React.ReactNode
  onClick: () => void
  variant: 'teal' | 'amber' | 'indigo' | 'green' | 'red'
  loadingKey?: string
  disabled?: boolean
}

function PrimaryButton({ cta, isLoading }: { cta: PrimaryCTA; isLoading: boolean }) {
  const variants = {
    teal:   'bg-teal-600 hover:bg-teal-700 text-white shadow-teal-100',
    amber:  'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-100',
    indigo: 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-100',
    green:  'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-100',
    red:    'bg-red-500 hover:bg-red-600 text-white shadow-red-100',
  }
  const isDisabled = isLoading || cta.disabled
  return (
    <motion.button
      whileHover={{ scale: isDisabled ? 1 : 1.02 }} whileTap={{ scale: isDisabled ? 1 : 0.97 }}
      onClick={cta.onClick}
      disabled={isDisabled}
      className={`flex items-center gap-3 px-5 py-2.5 rounded-xl text-sm font-semibold shadow-lg transition-all
        ${variants[cta.variant]} ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className="flex items-center gap-2">
        {isLoading
          ? <Loader2 className="w-4 h-4 animate-spin" />
          : cta.icon}
        <span className="flex flex-col items-start leading-tight">
          <span>{cta.label}</span>
          <span className="text-[10px] font-normal opacity-80">{cta.sublabel}</span>
        </span>
      </span>
      {!isLoading && <ChevronRight className="w-4 h-4 opacity-70" />}
    </motion.button>
  )
}

function SmallButton({
  label, icon, onClick, loading = false, disabled = false, variant = 'ghost',
}: {
  label: string; icon: React.ReactNode; onClick: () => void
  loading?: boolean; disabled?: boolean; variant?: 'ghost' | 'danger' | 'neutral'
}) {
  const variants = {
    ghost:   'text-gray-400 hover:text-gray-600 hover:bg-gray-50 border-transparent',
    neutral: 'text-gray-600 border-gray-200 hover:bg-gray-50 bg-white',
    danger:  'text-red-500 border-red-200 hover:bg-red-50 bg-white',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      title={label}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors
        ${variants[variant]} ${disabled || loading ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}

function OptimalBadge() {
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
      className="flex items-center gap-2.5 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-xl"
    >
      <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
      <div>
        <p className="text-sm font-semibold text-emerald-800">System Optimal</p>
        <p className="text-xs text-emerald-600">AI Judge verified no further rule improvements are possible</p>
      </div>
    </motion.div>
  )
}

export function ActionBar({
  status, hasReconcile, hasProposal, isOptimal, verifyVerdict,
  hasUpload,
  onReconcile, onJudge, onVerify, onVerifyGreedy, onApprove, onReject,
  onSeedDemo, onReset,
  loading, pipelineRunning,
}: Props) {
  const anyLoading = !!loading
  const blocked    = pipelineRunning || anyLoading

  // Derive the primary CTA based on pipeline state
  let primaryCTA: PrimaryCTA | null = null

  if (!hasReconcile) {
    primaryCTA = {
      label: 'Run Reconcile',
      sublabel: hasUpload ? 'Start the AI pipeline' : 'Upload data first to begin',
      icon: <Play className="w-4 h-4" />, onClick: onReconcile,
      variant: 'teal', loadingKey: 'reconcile',
      disabled: !hasUpload,
    }
  } else if (!hasProposal && !isOptimal) {
    primaryCTA = {
      label: 'Run AI Judge', sublabel: 'Analyze errors & propose rules',
      icon: <Brain className="w-4 h-4" />, onClick: onJudge,
      variant: 'amber', loadingKey: 'judge',
    }
  } else if (hasProposal && !isOptimal) {
    primaryCTA = {
      label: 'Verify Proposal', sublabel: 'Test on holdout data',
      icon: <Shield className="w-4 h-4" />, onClick: onVerify,
      variant: 'indigo', loadingKey: 'verify',
    }
  } else if (verifyVerdict === 'GENUINE_IMPROVEMENT' && onApprove) {
    primaryCTA = {
      label: 'Approve & Activate', sublabel: 'Apply improved rules',
      icon: <CheckCircle2 className="w-4 h-4" />, onClick: onApprove,
      variant: 'green', loadingKey: 'approve',
    }
  } else if (verifyVerdict === 'REWARD_HACKING' && onReject) {
    primaryCTA = {
      label: 'Reject Proposal', sublabel: 'Rules degraded holdout',
      icon: <XCircle className="w-4 h-4" />, onClick: onReject,
      variant: 'red', loadingKey: 'reject',
    }
  }

  const primaryLoading = primaryCTA ? loading === primaryCTA.loadingKey : false
  const showPipeline   = pipelineRunning && !primaryLoading

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3 space-y-2.5">

      <div className="flex items-center justify-between gap-4">
        {/* Primary CTA */}
        <div className="flex items-center gap-3">
          {isOptimal && !blocked ? (
            <OptimalBadge />
          ) : showPipeline ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin text-teal-500" />
              <span>Pipeline running automatically…</span>
            </div>
          ) : primaryCTA ? (
            <PrimaryButton cta={primaryCTA} isLoading={primaryLoading} />
          ) : null}
        </div>

        {/* Secondary utilities */}
        <div className="flex items-center gap-2">
          {status && (
            <span className="text-xs text-gray-400 font-mono hidden md:block">
              rules: <span className="text-teal-600 font-semibold">{status.current_rule_version}</span>
              {status.iteration_count > 0 && (
                <span className="ml-1.5 text-gray-300">· {status.iteration_count} iter</span>
              )}
            </span>
          )}

          <SmallButton
            label="Reward Hacking Test"
            icon={<AlertTriangle className="w-3 h-3" />}
            onClick={onVerifyGreedy}
            loading={loading === 'greedy'}
            disabled={blocked && loading !== 'greedy'}
            variant="danger"
          />

          <SmallButton
            label="Reset"
            icon={<RefreshCw className="w-3 h-3" />}
            onClick={() => { if (confirm('Reset all history and results?')) onReset() }}
            disabled={blocked}
            variant="ghost"
          />
        </div>
      </div>

      {/* Demo row */}
      <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
        <span className="text-[11px] text-gray-400 font-medium shrink-0">Demo:</span>
        <SmallButton
          label="⚡ Seed instant demo"
          icon={<Zap className="w-3 h-3" />}
          onClick={onSeedDemo}
          loading={loading === 'seed'}
          variant="neutral"
        />
        <span className="text-[11px] text-gray-300 hidden sm:block">
          Pre-computed results — no Gemini calls, ideal for live demos
        </span>
      </div>
    </div>
  )
}
