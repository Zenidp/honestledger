import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react'
import type { ReconcileReport } from '../types'
import { ProcessLog } from './ProcessLog'
import { CountdownTimer } from './CountdownTimer'

interface Props {
  report: ReconcileReport | null
  loading?: boolean
  logSteps?: string[]
  logRunning?: boolean
}

const DecisionBadge = ({ decision, confidence }: { decision: string; confidence: number }) => {
  if (decision === 'matched') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200">
      <CheckCircle2 className="w-3 h-3" /> matched
    </span>
  )
  if (decision === 'unmatched') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
      <XCircle className="w-3 h-3" /> unmatched
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
      <HelpCircle className="w-3 h-3" /> uncertain
    </span>
  )
}

export function ReconcileTable({ report, loading, logSteps = [], logRunning = false }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (id: string) => setExpanded(prev => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Reconciliation Results</h2>
          {report && (
            <p className="text-xs text-gray-500 mt-0.5">
              Rules: <span className="font-mono text-teal-600">{report.rule_version}</span>
            </p>
          )}
        </div>
        {report && (
          <div className="text-right">
            <div className="text-2xl font-bold text-teal-600">{(report.accuracy * 100).toFixed(0)}%</div>
            <div className="text-xs text-gray-400">{report.correct}/{report.total} correct</div>
          </div>
        )}
      </div>

      <div className="overflow-auto max-h-[420px] scrollbar-thin">
        {loading ? (
          <div className="px-5 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-teal-400 border-t-transparent rounded-full shrink-0" />
                Running reconciliation...
              </div>
              <CountdownTimer seconds={30} />
            </div>
            <ProcessLog steps={logSteps} running={logRunning} />
          </div>
        ) : !report ? (
          <div className="flex items-center justify-center h-32 text-sm text-gray-400">
            Click <span className="mx-1 font-mono bg-gray-100 px-1.5 py-0.5 rounded text-xs">Run Reconcile</span> to start
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium text-gray-500">Payment</th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-500">Decision</th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-500">Matched Invoice</th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-500">Conf.</th>
                <th className="px-4 py-2.5 text-left font-medium text-gray-500">
                  Rationale <span className="text-gray-300 font-normal">(click row to expand)</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              <AnimatePresence>
                {report.results.map((r, i) => {
                  const isExpanded = expanded.has(r.payment_id)
                  return (
                  <motion.tr key={r.payment_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.02 }}
                    onClick={() => toggle(r.payment_id)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-4 py-2.5 font-mono text-gray-700">{r.payment_id}</td>
                    <td className="px-4 py-2.5">
                      <DecisionBadge decision={r.decision} confidence={r.confidence} />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-gray-600">{r.matched_invoice_id ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-14 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-teal-400 transition-all"
                            style={{ width: `${r.confidence * 100}%` }} />
                        </div>
                        <span className="text-gray-500">{(r.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 max-w-sm">
                      <div className="flex items-start gap-1.5">
                        <p className={`text-gray-500 text-xs flex-1 ${isExpanded ? 'whitespace-normal' : 'line-clamp-2'}`}>
                          {r.rationale}
                        </p>
                        {isExpanded
                          ? <ChevronUp className="w-3 h-3 text-gray-300 shrink-0 mt-0.5" />
                          : <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 mt-0.5" />
                        }
                      </div>
                    </td>
                  </motion.tr>
                  )
                })}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
