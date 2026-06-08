import { Brain, ShieldCheck, BadgeCheck, ArrowRight } from 'lucide-react'
import { motion } from 'framer-motion'

interface Step {
  icon: React.ReactNode
  title: string
  desc: string
  active?: boolean
}

interface Props {
  hasReconcile: boolean
  hasProposal: boolean
  isOptimal: boolean
}

export function NextStepsPanel({ hasReconcile, hasProposal, isOptimal }: Props) {
  const steps: Step[] = [
    {
      icon: <Brain className="w-4 h-4" />,
      title: 'AI Judge analyses errors',
      desc: 'Gemini reviews unmatched payments, computes name similarity matrix, and proposes precise rule adjustments.',
      active: hasReconcile && !hasProposal && !isOptimal,
    },
    {
      icon: <ShieldCheck className="w-4 h-4" />,
      title: 'Verification Gate tests rules',
      desc: 'Proposed rules are evaluated on held-out data to prevent reward hacking and validate generalisation.',
      active: hasProposal && !isOptimal,
    },
    {
      icon: <BadgeCheck className="w-4 h-4" />,
      title: 'Auto-approve & loop',
      desc: 'Genuine improvements are activated automatically. The loop continues until the system reaches optimal accuracy.',
      active: false,
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-4"
    >
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">How it works</p>
        <p className="text-sm font-semibold text-gray-800 mt-0.5">
          {!hasReconcile
            ? 'Run Reconcile to start the AI pipeline'
            : hasReconcile && !hasProposal && !isOptimal
            ? 'AI Judge is next — analysing your results'
            : 'Verification Gate checks every proposed change'}
        </p>
      </div>

      <div className="space-y-3">
        {steps.map((s, i) => (
          <div key={i}
            className={`flex gap-3 p-3 rounded-lg transition-colors
              ${s.active ? 'bg-teal-50 border border-teal-100' : 'border border-transparent'}`}
          >
            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5
              ${s.active ? 'bg-teal-100 text-teal-600' : 'bg-gray-100 text-gray-400'}`}>
              {s.icon}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <p className={`text-xs font-semibold ${s.active ? 'text-teal-800' : 'text-gray-600'}`}>
                  {s.title}
                </p>
                {s.active && (
                  <span className="text-[10px] bg-teal-500 text-white rounded px-1.5 py-0.5 font-medium">Next</span>
                )}
              </div>
              <p className="text-[11px] text-gray-400 mt-0.5 leading-relaxed">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-gray-100">
        <p className="text-[11px] text-gray-400 leading-relaxed">
          <span className="font-medium text-gray-500">Anti reward-hacking</span> — the system uses a
          train/holdout split and frontier scoring to ensure every rule improvement genuinely generalises.
        </p>
      </div>
    </motion.div>
  )
}
