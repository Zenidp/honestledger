import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, HelpCircle, ChevronDown, ChevronUp, AlertTriangle, PlayCircle } from 'lucide-react'
import type { ReconcileReport } from '../types'
import { ProcessLog } from './ProcessLog'
import { ElapsedTimer } from './ElapsedTimer'

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
            <div className="text-xs text-gray-400">{report.correct}/{report.total} matched</div>
          </div>
        )}
      </div>

      {report && (() => {
        const unmatched = report.results.filter(r => r.decision === 'unmatched')
        if (unmatched.length === 0) return null
        return (
          <div className="border-b border-amber-100 bg-amber-50 px-5 py-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
              <span className="text-xs font-semibold text-amber-800">
                {unmatched.length} Payment{unmatched.length > 1 ? 's' : ''} Require Manual Review
              </span>
              <span className="text-xs text-amber-600">
                — tidak dapat di-match otomatis, perlu investigasi tim keuangan
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {unmatched.map(r => (
                <div key={r.payment_id} className="flex items-start gap-2 bg-white rounded-lg border border-amber-200 px-3 py-2">
                  <XCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <span className="font-mono text-xs font-medium text-gray-700">{r.payment_id}</span>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{r.rationale}</p>
                  </div>
                  <span className="ml-auto shrink-0 text-xs bg-amber-100 text-amber-700 border border-amber-200 rounded px-1.5 py-0.5 font-medium whitespace-nowrap">
                    review manual
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })()}

      <div className="overflow-auto max-h-[420px] scrollbar-thin">
        {loading ? (
          <div className="px-5 py-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm text-gray-600 font-medium">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-teal-500 border-t-transparent rounded-full shrink-0" />
                Running reconciliation…
              </div>
              <ElapsedTimer running={loading} />
            </div>
            <ProcessLog steps={logSteps} running={logRunning} />
          </div>
        ) : !report ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-center px-8">
            <div className="w-10 h-10 bg-teal-50 rounded-full flex items-center justify-center">
              <PlayCircle className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">No results yet</p>
              <p className="text-xs text-gray-400 mt-0.5">Upload your CSV files, then click <span className="font-semibold text-teal-600">Run Reconcile</span> to start</p>
            </div>
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
                    className={`cursor-pointer transition-colors ${r.decision === 'unmatched' ? 'bg-amber-50/40 hover:bg-amber-50' : 'hover:bg-gray-50'}`}>
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
