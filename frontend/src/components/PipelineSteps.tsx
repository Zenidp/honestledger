import { CheckCircle2, Loader2, Upload, PlayCircle, Brain, ShieldCheck, BadgeCheck } from 'lucide-react'
import { motion } from 'framer-motion'

export type StepStatus = 'done' | 'active' | 'running' | 'pending'

export interface PipelineStep {
  id: string
  label: string
  detail?: string
  status: StepStatus
  icon: React.ReactNode
}

function StepNode({ step, isLast }: { step: PipelineStep; isLast: boolean }) {
  const colors: Record<StepStatus, string> = {
    done:    'bg-teal-500 text-white',
    active:  'bg-teal-600 text-white ring-4 ring-teal-100',
    running: 'bg-amber-500 text-white ring-4 ring-amber-100',
    pending: 'bg-gray-100 text-gray-400',
  }
  const labelColors: Record<StepStatus, string> = {
    done:    'text-teal-700 font-semibold',
    active:  'text-teal-700 font-semibold',
    running: 'text-amber-700 font-semibold',
    pending: 'text-gray-400 font-normal',
  }

  return (
    <div className="flex items-center flex-1 min-w-0">
      <div className="flex flex-col items-center gap-1.5 px-1 sm:px-2">
        <motion.div
          animate={step.status === 'active' ? { scale: [1, 1.05, 1] } : {}}
          transition={{ repeat: Infinity, duration: 2 }}
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${colors[step.status]}`}
        >
          {step.status === 'running'
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : step.status === 'done'
            ? <CheckCircle2 className="w-4 h-4" />
            : <span className="text-inherit">{step.icon}</span>}
        </motion.div>
        <div className="text-center min-w-[56px]">
          <p className={`text-[11px] leading-tight transition-colors ${labelColors[step.status]}`}>
            {step.label}
          </p>
          {step.detail && (
            <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">{step.detail}</p>
          )}
        </div>
      </div>
      {!isLast && (
        <div className="flex-1 h-px mx-1 transition-colors duration-500"
          style={{ background: step.status === 'done' ? '#14b8a6' : '#e5e7eb' }} />
      )}
    </div>
  )
}

interface Props {
  steps: PipelineStep[]
}

export function PipelineSteps({ steps }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3">
      <div className="flex items-start">
        {steps.map((step, i) => (
          <StepNode key={step.id} step={step} isLast={i === steps.length - 1} />
        ))}
      </div>
    </div>
  )
}

// Helper to derive pipeline steps from App state
export function derivePipelineSteps(opts: {
  hasReconcile: boolean
  hasProposal: boolean
  isOptimal: boolean
  hasVerify: boolean
  verifyVerdict?: string | null
  loading: string | null
  reconcileAccuracy?: number
  proposalVersion?: string
}): PipelineStep[] {
  const { hasReconcile, hasProposal, isOptimal, hasVerify, verifyVerdict, loading, reconcileAccuracy, proposalVersion } = opts

  const reconcileRunning = loading === 'reconcile'
  const judgeRunning     = loading === 'judge'
  const verifyRunning    = loading === 'verify' || loading === 'greedy'
  const approveRunning   = loading === 'approve'

  // Step 1: Reconcile
  const reconcileStatus: StepStatus =
    reconcileRunning ? 'running' :
    hasReconcile     ? 'done' :
                       'active'

  // Step 2: Judge
  const judgeStatus: StepStatus =
    judgeRunning                     ? 'running' :
    (hasProposal || isOptimal)       ? 'done' :
    hasReconcile                     ? 'active' :
                                       'pending'

  // Step 3: Verify
  const verifyStatus: StepStatus =
    verifyRunning                         ? 'running' :
    hasVerify                             ? 'done' :
    (hasProposal && !isOptimal)           ? 'active' :
                                            'pending'

  // Step 4: Result
  const resultStatus: StepStatus =
    approveRunning                                             ? 'running' :
    isOptimal                                                  ? 'done' :
    verifyVerdict === 'GENUINE_IMPROVEMENT'                    ? 'active' :
    verifyVerdict === 'REWARD_HACKING'                         ? 'done' :
    hasVerify                                                  ? 'active' :
                                                                 'pending'

  return [
    {
      id: 'reconcile',
      label: 'Reconcile',
      detail: reconcileAccuracy !== undefined ? `${Math.round(reconcileAccuracy * 100)}% matched` : undefined,
      status: reconcileStatus,
      icon: <PlayCircle className="w-4 h-4" />,
    },
    {
      id: 'judge',
      label: 'AI Judge',
      detail: isOptimal ? 'Optimal' : proposalVersion ? proposalVersion : undefined,
      status: judgeStatus,
      icon: <Brain className="w-4 h-4" />,
    },
    {
      id: 'verify',
      label: 'Verify',
      detail: verifyVerdict === 'GENUINE_IMPROVEMENT' ? '✓ Passed' :
              verifyVerdict === 'REWARD_HACKING' ? '⚠ Blocked' :
              verifyVerdict === 'INCONCLUSIVE' ? 'Retrying' : undefined,
      status: verifyStatus,
      icon: <ShieldCheck className="w-4 h-4" />,
    },
    {
      id: 'result',
      label: 'Result',
      detail: isOptimal ? 'System optimal' :
              verifyVerdict === 'GENUINE_IMPROVEMENT' ? 'Approving' : undefined,
      status: resultStatus,
      icon: <BadgeCheck className="w-4 h-4" />,
    },
  ]
}
