import { motion } from 'framer-motion'
import { ShieldCheck, ShieldAlert, Shield, ShieldOff } from 'lucide-react'
import type { VerifyReport } from '../types'
import { ProcessLog } from './ProcessLog'
import { CountdownTimer } from './CountdownTimer'

interface Props {
  report: VerifyReport | null
  loading?: boolean
  logSteps?: string[]
  logRunning?: boolean
}

function ScoreBar({ label, baseline, score, delta }: {
  label: string; baseline: number; score: number; delta: number
}) {
  const isUp = delta > 0.005
  const isDown = delta < -0.005
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="font-medium text-gray-600">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{(baseline * 100).toFixed(0)}%</span>
          <span className="text-gray-300">→</span>
          <span className={`font-bold ${isUp ? 'text-teal-600' : isDown ? 'text-red-500' : 'text-gray-700'}`}>
            {(score * 100).toFixed(0)}%
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
            isUp ? 'bg-teal-50 text-teal-600' :
            isDown ? 'bg-red-50 text-red-500' :
            'bg-gray-100 text-gray-400'
          }`}>
            {delta > 0 ? '+' : ''}{(delta * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <motion.div className="h-full rounded-full"
          initial={{ width: `${baseline * 100}%` }}
          animate={{ width: `${score * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{
            background: isUp ? '#14b8a6' : isDown ? '#ef4444' : '#94a3b8'
          }} />
      </div>
    </div>
  )
}

const verdictConfig = {
  GENUINE_IMPROVEMENT: {
    icon: ShieldCheck,
    label: 'Genuine Improvement',
    bg: 'bg-teal-50',
    border: 'border-teal-200',
    text: 'text-teal-700',
    iconColor: 'text-teal-500',
  },
  REWARD_HACKING: {
    icon: ShieldAlert,
    label: 'Reward Hacking Detected',
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    iconColor: 'text-red-500',
  },
  INCONCLUSIVE: {
    icon: Shield,
    label: 'Inconclusive',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-600',
    iconColor: 'text-gray-400',
  },
  HARD_BLOCK: {
    icon: ShieldOff,
    label: 'Hard Block — Admin Escalation Required',
    bg: 'bg-orange-50',
    border: 'border-orange-300',
    text: 'text-orange-800',
    iconColor: 'text-orange-500',
  },
}

export function VerificationGate({ report, loading, logSteps = [], logRunning = false }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">Verification Gate</h2>
        <p className="text-xs text-gray-400 mt-0.5">Train vs holdout — reward hacking detector</p>
      </div>

      <div className="p-5">
        {loading ? (
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-teal-400 border-t-transparent rounded-full shrink-0" />
                Running holdout verification...
              </div>
              <CountdownTimer seconds={150} />
            </div>
            <ProcessLog steps={logSteps} running={logRunning} />
          </div>
        ) : !report ? (
          <p className="text-sm text-gray-400">Run verify to test proposal against holdout data.</p>
        ) : (
          <div className="space-y-5">
            <div className="space-y-3">
              <ScoreBar label="Train accuracy"
                baseline={report.score_baseline_train} score={report.score_train}
                delta={report.delta_train} />
              <ScoreBar label="Holdout (anchor)"
                baseline={report.score_baseline_holdout} score={report.score_holdout}
                delta={report.delta_holdout} />
              {report.score_frontier != null && report.score_baseline_frontier != null && report.delta_frontier != null && (
                <div className="relative">
                  <ScoreBar label="Holdout (frontier)"
                    baseline={report.score_baseline_frontier} score={report.score_frontier}
                    delta={report.delta_frontier} />
                  <span className={`absolute right-0 top-0 text-xs px-1.5 py-0.5 rounded font-medium ${
                    report.frontier_passed ? 'bg-teal-50 text-teal-600' : 'bg-red-50 text-red-500'
                  }`}>
                    {report.frontier_passed ? '✓ frontier ok' : '✗ frontier fail'}
                  </span>
                </div>
              )}
            </div>

            {/* Tier + consecutive failures badge */}
            {(report.tier != null || report.consecutive_failures > 0) && (
              <div className="flex items-center gap-2 text-xs">
                {report.tier != null && (
                  <span className={`px-2 py-0.5 rounded-full border font-medium ${
                    report.tier === 1 ? 'bg-teal-50 text-teal-600 border-teal-200' :
                    report.tier === 3 ? 'bg-orange-50 text-orange-700 border-orange-200' :
                    'bg-yellow-50 text-yellow-700 border-yellow-200'
                  }`}>
                    Tier {report.tier}
                  </span>
                )}
                {report.consecutive_failures > 0 && (
                  <span className="px-2 py-0.5 rounded-full border bg-gray-50 text-gray-500 border-gray-200 font-medium">
                    {report.consecutive_failures} inconclusive streak
                  </span>
                )}
              </div>
            )}

            {(() => {
              const cfg = verdictConfig[report.verdict] ?? verdictConfig['INCONCLUSIVE']
              const Icon = cfg.icon
              return (
                <motion.div
                  initial={{ scale: 0.95, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className={`rounded-lg border p-4 ${cfg.bg} ${cfg.border}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon className={`w-4 h-4 ${cfg.iconColor}`} />
                    <span className={`text-sm font-semibold ${cfg.text}`}>{cfg.label}</span>
                  </div>
                  <p className={`text-xs leading-relaxed ${cfg.text} opacity-80`}>{report.explanation}</p>
                </motion.div>
              )
            })()}
          </div>
        )}
      </div>
    </div>
  )
}
