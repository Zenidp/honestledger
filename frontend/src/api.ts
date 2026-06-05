import axios from 'axios'
import type {
  ReconcileReport, RuleProposal, VerifyReport,
  AppStatus, IterationRecord, RuleSet
} from './types'

const api = axios.create({ baseURL: '/api' })

export const getHealth = () => api.get('/health')
export const getStatus = (): Promise<AppStatus> =>
  api.get<AppStatus>('/status').then(r => r.data)

export const getAllRules = (): Promise<{ current_version: string; versions: Record<string, RuleSet> }> =>
  api.get('/rules').then(r => r.data)

export const runReconcile = (split = 'train', rule_version?: string): Promise<ReconcileReport> =>
  api.post<ReconcileReport>('/reconcile', { split, rule_version }).then(r => r.data)

export const runJudge = (next_version = 'v2'): Promise<RuleProposal> =>
  api.post<RuleProposal>('/judge', { next_version }).then(r => r.data)

export const runVerify = (): Promise<{ job_id: string; status: string }> =>
  api.post('/verify').then(r => r.data)

export const runVerifyGreedy = (base_version?: string): Promise<{ job_id: string; status: string }> =>
  api.post('/verify/greedy', { base_version }).then(r => r.data)

export const getJob = (job_id: string): Promise<{ status: string; result: VerifyReport | null; error: string | null }> =>
  api.get(`/jobs/${job_id}`).then(r => r.data)

export const approveProposal = (): Promise<{ approved: boolean; active_version: string }> =>
  api.post('/approve', {}).then(r => r.data)

export const rejectProposal = (): Promise<{ rejected: boolean; active_version: string }> =>
  api.post('/reject').then(r => r.data)

export const getHistory = (): Promise<{ iterations: IterationRecord[] }> =>
  api.get('/history').then(r => r.data)

export const resetHistory = () => api.post('/history/reset')

export const getLatestReconcile = (): Promise<ReconcileReport> =>
  api.get<ReconcileReport>('/reconcile/latest').then(r => r.data)

export const getLatestProposal = (): Promise<RuleProposal> =>
  api.get<RuleProposal>('/judge/latest').then(r => r.data)

export const getLatestVerify = (): Promise<VerifyReport> =>
  api.get<VerifyReport>('/verify/latest').then(r => r.data)

export const seedDemo = () => api.post('/demo/seed').then(r => r.data)
export const seedHacking = () => api.post('/demo/seed-hacking').then(r => r.data)
