import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ShieldCheck, Activity, Download, LogOut, ChevronDown, FileText, Table2, FileCheck } from 'lucide-react'

import { ReconcileTable } from './components/ReconcileTable'
import { RuleProposalCard } from './components/RuleProposalCard'
import { VerificationGate } from './components/VerificationGate'
import { RewardHackBanner } from './components/RewardHackBanner'
import { ApprovalControls } from './components/ApprovalControls'
import { AccuracyChart } from './components/AccuracyChart'
import { ActionBar } from './components/ActionBar'
import ApiKeyGate from './components/ApiKeyGate'
import UploadPanel from './components/UploadPanel'

import * as api from './api'
import type {
  ReconcileReport, RuleProposal, VerifyReport,
  AppStatus, IterationRecord
} from './types'

const RECONCILE_STEPS = [
  'Initializing reconciliation engine...',
  'Loading payment dataset...',
  'Applying name similarity filter...',
  'Matching payments to invoice candidates...',
  'Running LLM judgment on ambiguous matches...',
  'Scoring and finalizing results...',
]

const JUDGE_STEPS = [
  'Analyzing reconciliation failure patterns...',
  'Identifying root causes of mismatches...',
  'Generating rule improvement proposal...',
  'Validating proposed parameter changes...',
]

export default function App() {
  const [authenticated, setAuthenticated] = useState(api.hasApiKey())
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [reconcile, setReconcile] = useState<ReconcileReport | null>(null)
  const [proposal, setProposal] = useState<RuleProposal | null>(null)
  const [verifyReport, setVerifyReport] = useState<VerifyReport | null>(null)
  const [history, setHistory] = useState<IterationRecord[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [showBanner, setShowBanner] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [logSteps, setLogSteps] = useState<string[]>([])
  const [logRunning, setLogRunning] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const logTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startSimulatedLog = (steps: string[], intervalMs = 2200) => {
    if (logTimerRef.current !== null) {
      clearInterval(logTimerRef.current)
      logTimerRef.current = null
    }
    setLogSteps([])
    setLogRunning(true)
    let count = 0
    const timerId = setInterval(() => {
      count++
      // Set exact slice — no append, no race condition
      setLogSteps(steps.slice(0, count))
      if (count >= steps.length) {
        clearInterval(timerId)
        if (logTimerRef.current === timerId) logTimerRef.current = null
      }
    }, intervalMs)
    logTimerRef.current = timerId
    return () => {
      clearInterval(timerId)
      if (logTimerRef.current === timerId) logTimerRef.current = null
      setLogRunning(false)
    }
  }

  const refreshStatus = useCallback(async () => {
    if (!api.hasApiKey()) return
    try {
      const s = await api.getStatus()
      setStatus(s)
    } catch { /* backend not yet up or 401 */ }
  }, [])

  const refreshHistory = useCallback(async () => {
    const h = await api.getHistory()
    setHistory(h.iterations)
  }, [])

  useEffect(() => {
    if (!authenticated) return
    refreshStatus()
    const interval = setInterval(refreshStatus, 5000)
    return () => clearInterval(interval)
  }, [authenticated, refreshStatus])

  const withLoading = async (key: string, fn: () => Promise<void>) => {
    setLoading(key)
    setError(null)
    try {
      await fn()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally {
      setLoading(null)
      await refreshStatus()
    }
  }

  const handleReconcile = async () => {
    const stop = startSimulatedLog(RECONCILE_STEPS)
    setLoading('reconcile'); setError(null)
    try {
      const report = await api.runReconcile('train')
      stop()
      setLogSteps([...RECONCILE_STEPS, `✓ Done — ${report.correct}/${report.total} matched (${Math.round(report.accuracy * 100)}% accuracy)`])
      setReconcile(report)
      setProposal(null); setVerifyReport(null); setShowBanner(false)
    } catch (e: any) {
      stop()
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally {
      setLoading(null); await refreshStatus()
    }
  }

  const handleJudge = async () => {
    const stop = startSimulatedLog(JUDGE_STEPS, 2500)
    setLoading('judge'); setError(null)
    try {
      const p = await api.runJudge()
      stop()
      setLogSteps([...JUDGE_STEPS, `✓ Proposal generated — ${p.rule_version}`])
      setProposal(p); setVerifyReport(null); setShowBanner(false)
    } catch (e: any) {
      stop()
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally {
      setLoading(null); await refreshStatus()
    }
  }

  const pollJob = async (job_id: string, onDone: (result: VerifyReport) => void) => {
    setLogSteps(['Starting verification job...'])
    setLogRunning(true)
    return new Promise<void>((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const job = await api.getJob(job_id)
          if (job.progress?.steps?.length) {
            setLogSteps(job.progress.steps)
          }
          if (job.status === 'done' && job.result) {
            clearInterval(interval)
            setLogRunning(false)
            onDone(job.result)
            resolve()
          } else if (job.status === 'error') {
            clearInterval(interval)
            setLogRunning(false)
            reject(new Error(job.error ?? 'Job failed'))
          }
        } catch (e) { clearInterval(interval); setLogRunning(false); reject(e) }
      }, 3000)
    })
  }

  const handleVerify = async () => {
    setLoading('verify'); setError(null)
    try {
      const { job_id } = await api.runVerify()
      await pollJob(job_id, result => {
        setVerifyReport(result)
        if (result.verdict === 'REWARD_HACKING') setShowBanner(true)
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally { setLoading(null); await refreshStatus() }
  }

  const handleVerifyGreedy = async () => {
    setLoading('greedy'); setError(null)
    try {
      const { job_id } = await api.runVerifyGreedy()
      await pollJob(job_id, result => {
        setVerifyReport(result)
        if (result.verdict === 'REWARD_HACKING') setShowBanner(true)
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally { setLoading(null); await refreshStatus() }
  }

  const handleApprove = () => withLoading('approve', async () => {
    await api.approveProposal()
    setProposal(null); setVerifyReport(null); setShowBanner(false)
    await refreshHistory()
  })

  const handleReject = () => withLoading('reject', async () => {
    await api.rejectProposal()
    setProposal(null); setVerifyReport(null); setShowBanner(false)
    await refreshHistory()
  })

  const handleSeedDemo = () => withLoading('seed', async () => {
    await api.seedDemo()
    const [rec, prop, ver, hist] = await Promise.all([
      api.getLatestReconcile().catch(() => null),
      api.getLatestProposal().catch(() => null),
      api.getLatestVerify().catch(() => null),
      api.getHistory(),
    ])
    if (rec) setReconcile(rec)
    if (prop) setProposal(prop)
    if (ver) { setVerifyReport(ver); if (ver.verdict === 'REWARD_HACKING') setShowBanner(true) }
    setHistory(hist.iterations)
  })

  const handleReset = () => withLoading('reset', async () => {
    await api.resetHistory()
    setReconcile(null); setProposal(null); setVerifyReport(null)
    setHistory([]); setShowBanner(false)
  })

  const handleLogout = () => {
    api.clearApiKey()
    setAuthenticated(false)
    setStatus(null); setReconcile(null); setProposal(null)
    setVerifyReport(null); setHistory([])
  }

  // ── Auth gate ────────────────────────────────────────────────────────────────
  if (!authenticated) {
    return <ApiKeyGate onAuthenticated={() => setAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <RewardHackBanner
        visible={showBanner}
        explanation={verifyReport?.explanation}
        onDismiss={() => setShowBanner(false)}
      />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-teal-600 rounded-lg flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-4.5 h-4.5 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-900 leading-tight">HonestLedger</h1>
              <p className="text-xs text-gray-400 leading-tight">The reconciliation agent that keeps itself honest</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {status && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex items-center gap-1.5 text-xs text-gray-500">
                <Activity className="w-3.5 h-3.5 text-teal-500" />
                <span className="font-mono text-teal-600 font-medium">{status.current_rule_version}</span>
                <span className="text-gray-300">·</span>
                <span>{status.iteration_count} iterations</span>
                {status.tenant_name && (
                  <>
                    <span className="text-gray-300">·</span>
                    <span className="text-gray-500">{status.tenant_name}</span>
                  </>
                )}
              </motion.div>
            )}

            {/* Export dropdown */}
            {reconcile && (
              <div className="relative">
                <button
                  onClick={() => setShowExportMenu(v => !v)}
                  className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-teal-600 border border-gray-200 hover:border-teal-300 px-2.5 py-1.5 rounded-lg transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export
                  <ChevronDown className="w-3 h-3" />
                </button>
                <AnimatePresence>
                  {showExportMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.12 }}
                      className="absolute right-0 top-full mt-1.5 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50"
                    >
                      <button onClick={() => { api.exportReconcile('audit_csv'); setShowExportMenu(false) }}
                        className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2.5">
                        <FileText className="w-3.5 h-3.5 text-gray-400" />
                        <div>
                          <p className="font-medium">Audit CSV</p>
                          <p className="text-gray-400 text-[10px]">Full detail + rationale</p>
                        </div>
                      </button>
                      <button onClick={() => { api.exportReconcile('accounting_csv'); setShowExportMenu(false) }}
                        className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2.5">
                        <Table2 className="w-3.5 h-3.5 text-gray-400" />
                        <div>
                          <p className="font-medium">Accounting CSV</p>
                          <p className="text-gray-400 text-[10px]">Clean for ERP / Excel</p>
                        </div>
                      </button>
                      <div className="border-t border-gray-100 my-1" />
                      <button onClick={() => { api.exportReconcile('audit_pdf'); setShowExportMenu(false) }}
                        className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2.5">
                        <FileCheck className="w-3.5 h-3.5 text-teal-500" />
                        <div>
                          <p className="font-medium text-teal-700">Audit PDF</p>
                          <p className="text-gray-400 text-[10px]">Formal report document</p>
                        </div>
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Upload toggle */}
            <button
              onClick={() => setShowUpload(v => !v)}
              className="text-xs text-gray-500 hover:text-teal-600 border border-gray-200 hover:border-teal-300 px-2.5 py-1.5 rounded-lg transition-colors"
            >
              Upload Data
            </button>

            {/* Logout */}
            <button onClick={handleLogout} title="Sign out"
              className="text-gray-400 hover:text-red-500 transition-colors p-1">
              <LogOut className="w-4 h-4" />
            </button>

            <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" title="Connected" />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-5">

        {error && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
            className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            ⚠ {error}
          </motion.div>
        )}

        {/* Upload panel (collapsible) */}
        {showUpload && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
            <UploadPanel onUploaded={() => { setShowUpload(false); refreshStatus() }} />
          </motion.div>
        )}

        <ActionBar
          status={status}
          hasReconcile={reconcile !== null}
          hasProposal={proposal !== null}
          onReconcile={handleReconcile}
          onJudge={handleJudge}
          onVerify={handleVerify}
          onVerifyGreedy={handleVerifyGreedy}
          onSeedDemo={handleSeedDemo}
          onReset={handleReset}
          loading={loading}
        />


        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          <div className="lg:col-span-3 space-y-5">
            <ReconcileTable
              report={reconcile}
              loading={loading === 'reconcile'}
              logSteps={logSteps}
              logRunning={logRunning}
            />
            <AccuracyChart history={history} />
          </div>
          <div className="lg:col-span-2 space-y-5">
            <RuleProposalCard
              proposal={proposal}
              loading={loading === 'judge'}
              logSteps={loading === 'judge' ? logSteps : []}
              logRunning={loading === 'judge' ? logRunning : false}
            />
            <VerificationGate
              report={verifyReport}
              loading={loading === 'verify' || loading === 'greedy'}
              logSteps={loading === 'verify' || loading === 'greedy' ? logSteps : []}
              logRunning={loading === 'verify' || loading === 'greedy' ? logRunning : false}
            />
            <ApprovalControls
              verifyReport={verifyReport}
              onApprove={handleApprove}
              onReject={handleReject}
              loading={loading === 'approve' || loading === 'reject'}
            />
          </div>
        </div>

        <div className="text-center text-xs text-gray-300 pb-4">
          HonestLedger · Google Cloud Rapid Agent Hackathon · Arize Track
        </div>
      </main>
    </div>
  )
}
