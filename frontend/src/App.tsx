import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, Activity } from 'lucide-react'

import { ReconcileTable } from './components/ReconcileTable'
import { RuleProposalCard } from './components/RuleProposalCard'
import { VerificationGate } from './components/VerificationGate'
import { RewardHackBanner } from './components/RewardHackBanner'
import { ApprovalControls } from './components/ApprovalControls'
import { AccuracyChart } from './components/AccuracyChart'
import { ActionBar } from './components/ActionBar'

import * as api from './api'
import type {
  ReconcileReport, RuleProposal, VerifyReport,
  AppStatus, IterationRecord
} from './types'

export default function App() {
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [reconcile, setReconcile] = useState<ReconcileReport | null>(null)
  const [proposal, setProposal] = useState<RuleProposal | null>(null)
  const [verifyReport, setVerifyReport] = useState<VerifyReport | null>(null)
  const [history, setHistory] = useState<IterationRecord[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [showBanner, setShowBanner] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.getStatus()
      setStatus(s)
    } catch { /* backend not yet up */ }
  }, [])

  const refreshHistory = useCallback(async () => {
    const h = await api.getHistory()
    setHistory(h.iterations)
  }, [])

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 5000)
    return () => clearInterval(interval)
  }, [refreshStatus])

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

  const handleReconcile = () => withLoading('reconcile', async () => {
    const report = await api.runReconcile('train')
    setReconcile(report)
    setProposal(null)
    setVerifyReport(null)
    setShowBanner(false)
  })

  const handleJudge = () => withLoading('judge', async () => {
    const p = await api.runJudge()
    setProposal(p)
    setVerifyReport(null)
    setShowBanner(false)
  })

  const handleVerify = () => withLoading('verify', async () => {
    const r = await api.runVerify()
    setVerifyReport(r)
    if (r.verdict === 'REWARD_HACKING') setShowBanner(true)
  })

  const handleVerifyGreedy = async () => {
    setLoading('greedy')
    setError(null)
    try {
      // Start background job — returns immediately with job_id
      const { job_id } = await api.runVerifyGreedy()

      // Poll until done (Gemini calls run in backend thread)
      const poll = (): Promise<void> => new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
          try {
            const job = await api.getJob(job_id)
            if (job.status === 'done' && job.result) {
              clearInterval(interval)
              setVerifyReport(job.result)
              if (job.result.verdict === 'REWARD_HACKING') setShowBanner(true)
              resolve()
            } else if (job.status === 'error') {
              clearInterval(interval)
              reject(new Error(job.error ?? 'Verify job failed'))
            }
          } catch (e) {
            clearInterval(interval)
            reject(e)
          }
        }, 5000)  // poll every 5 seconds
      })

      await poll()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally {
      setLoading(null)
      await refreshStatus()
    }
  }

  const handleApprove = () => withLoading('approve', async () => {
    await api.approveProposal()
    setProposal(null)
    setVerifyReport(null)
    setShowBanner(false)
    await refreshHistory()
  })

  const handleReject = () => withLoading('reject', async () => {
    await api.rejectProposal()
    setProposal(null)
    setVerifyReport(null)
    setShowBanner(false)
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
    if (ver) {
      setVerifyReport(ver)
      if (ver.verdict === 'REWARD_HACKING') setShowBanner(true)
    }
    setHistory(hist.iterations)
  })

  const handleReset = () => withLoading('reset', async () => {
    await api.resetHistory()
    setReconcile(null)
    setProposal(null)
    setVerifyReport(null)
    setHistory([])
    setShowBanner(false)
  })

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Reward Hacking Banner */}
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
              </motion.div>
            )}
            <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" title="Connected to backend" />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-5">

        {/* Error */}
        {error && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
            className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            ⚠ {error}
          </motion.div>
        )}

        {/* Action bar */}
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

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

          {/* Left: Reconcile table (wider) */}
          <div className="lg:col-span-3 space-y-5">
            <ReconcileTable report={reconcile} loading={loading === 'reconcile'} />
            <AccuracyChart history={history} />
          </div>

          {/* Right: Judge + Verify + Approval */}
          <div className="lg:col-span-2 space-y-5">
            <RuleProposalCard proposal={proposal} loading={loading === 'judge'} />
            <VerificationGate report={verifyReport} loading={loading === 'verify' || loading === 'greedy'} />
            <ApprovalControls
              verifyReport={verifyReport}
              onApprove={handleApprove}
              onReject={handleReject}
              loading={loading === 'approve' || loading === 'reject'}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-gray-300 pb-4">
          HonestLedger · Google Cloud Rapid Agent Hackathon · Arize Track
        </div>
      </main>
    </div>
  )
}
