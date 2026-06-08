import axios from 'axios'
import type {
  ReconcileReport, RuleProposal, VerifyReport,
  AppStatus, IterationRecord, RuleSet
} from './types'

// API key stored in localStorage — sent as X-API-Key header on every request
const getApiKey = () => localStorage.getItem('hl_api_key') || ''

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(config => {
  const key = getApiKey()
  if (key) config.headers['X-API-Key'] = key
  return config
})

export const setApiKey = (key: string) => localStorage.setItem('hl_api_key', key)
export const clearApiKey = () => localStorage.removeItem('hl_api_key')
export const hasApiKey = () => !!getApiKey()

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

export const getJob = (job_id: string): Promise<{
  status: string
  result: VerifyReport | null
  error: string | null
  progress: { steps: string[] } | null
}> => api.get(`/jobs/${job_id}`).then(r => r.data)

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

// Upload CSV files
export const uploadData = (paymentsFile: File, invoicesFile: File, groundTruthFile?: File | null) => {
  const form = new FormData()
  form.append('payments_file', paymentsFile)
  form.append('invoices_file', invoicesFile)
  if (groundTruthFile) form.append('ground_truth_file', groundTruthFile)
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

// Export reconciliation results — format: audit_csv | accounting_csv | audit_pdf
export const exportReconcile = (format: 'audit_csv' | 'accounting_csv' | 'audit_pdf' = 'audit_csv') => {
  const key = getApiKey()
  const url = `/api/reconcile/export?format=${format}`
  const ext = format === 'audit_pdf' ? 'pdf' : 'csv'
  const label = format === 'audit_csv' ? 'audit' : format === 'accounting_csv' ? 'accounting' : 'audit'
  fetch(url, { headers: { 'X-API-Key': key } })
    .then(r => {
      if (!r.ok) throw new Error(`Export failed (${r.status})`)
      return r.blob()
    })
    .then(blob => {
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `reconciliation_${label}.${ext}`
      link.click()
    })
    .catch(err => alert(err.message))
}
