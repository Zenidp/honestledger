import { motion } from 'framer-motion'
import { Lightbulb, ArrowRight } from 'lucide-react'
import type { RuleProposal } from '../types'

interface Props {
  proposal: RuleProposal | null
  loading?: boolean
}

export function RuleProposalCard({ proposal, loading }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-amber-500" />
        <h2 className="text-sm font-semibold text-gray-800">Judge's Rule Proposal</h2>
      </div>

      <div className="p-5">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full" />
            Analysing traces...
          </div>
        ) : !proposal ? (
          <p className="text-sm text-gray-400">Run judge to get a rule improvement proposal.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Proposal</p>
              <p className="text-sm text-gray-700">{proposal.description}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Changes</p>
              <div className="space-y-1.5">
                {proposal.changes.map((c, i) => {
                  const [param, val] = c.split('=')
                  return (
                    <motion.div key={i}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-2 font-mono text-xs bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                      <span className="text-gray-500">{param}</span>
                      <ArrowRight className="w-3 h-3 text-gray-300 flex-shrink-0" />
                      <span className="text-teal-600 font-medium">{val}</span>
                    </motion.div>
                  )
                })}
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Rationale</p>
              <p className="text-xs text-gray-500 leading-relaxed">{proposal.rationale}</p>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded font-mono">
                → {proposal.rule_version}
              </span>
              <span className="text-xs text-gray-400">proposed by {proposal.proposed_by}</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
