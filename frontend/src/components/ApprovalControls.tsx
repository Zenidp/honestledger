import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, RotateCcw, Loader2 } from 'lucide-react'
import type { VerifyReport } from '../types'

interface Props {
  verifyReport: VerifyReport | null
  onApprove: () => void
  onReject: () => void
  loading?: boolean
}

export function ApprovalControls({ verifyReport, onApprove, onReject, loading }: Props) {
  const canApprove = verifyReport?.verdict === 'GENUINE_IMPROVEMENT'
  const hasDecision = !!verifyReport

  return (
    <AnimatePresence>
      {hasDecision && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          className="bg-white rounded-xl border border-gray-200 shadow-sm p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-800">Human Decision Required</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Review the verification results above and decide.
              </p>
            </div>
            <div className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${
              canApprove
                ? 'bg-teal-50 text-teal-700 border-teal-200'
                : 'bg-red-50 text-red-600 border-red-200'
            }`}>
              {canApprove ? '✓ Ready to approve' : '⚠ Approval blocked'}
            </div>
          </div>

          <div className="flex gap-3">
            <motion.button
              whileHover={canApprove ? { scale: 1.02 } : {}}
              whileTap={canApprove ? { scale: 0.98 } : {}}
              onClick={canApprove ? onApprove : undefined}
              disabled={!canApprove || loading}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                canApprove && !loading
                  ? 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              Approve & Activate
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onReject}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all"
            >
              <XCircle className="w-4 h-4" />
              Reject
            </motion.button>
          </div>

          {!canApprove && verifyReport && (
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="mt-3 text-xs text-red-500 flex items-center gap-1.5">
              <RotateCcw className="w-3 h-3" />
              Cannot approve: verdict is <strong>{verifyReport.verdict}</strong>. Approve only available for GENUINE_IMPROVEMENT.
            </motion.p>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
