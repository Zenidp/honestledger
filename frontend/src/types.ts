export type MatchDecision = 'matched' | 'unmatched' | 'uncertain'
export type VerifyVerdict = 'GENUINE_IMPROVEMENT' | 'REWARD_HACKING' | 'INCONCLUSIVE' | 'HARD_BLOCK'

export interface MatchResult {
  payment_id: string
  decision: MatchDecision
  matched_invoice_id: string | null
  confidence: number
  rationale: string
}

export interface ReconcileReport {
  results: MatchResult[]
  accuracy: number
  total: number
  correct: number
  rule_version: string
}

export interface RuleSet {
  version: string
  name_similarity_threshold: number
  amount_tolerance_abs: number
  amount_tolerance_pct: number
  date_tolerance_days: number
  min_confidence: number
  cluster_tag: string | null
}

export interface RuleProposal {
  rule_version: string
  description: string
  changes: string[]
  rationale: string
  proposed_by: string
  cluster_tag: string | null
}

export interface VerifyReport {
  rule_version: string
  score_train: number
  score_holdout: number
  score_baseline_train: number
  score_baseline_holdout: number
  delta_train: number
  delta_holdout: number
  verdict: VerifyVerdict
  explanation: string
  tier: number
  consecutive_failures: number
  score_frontier: number | null
  score_baseline_frontier: number | null
  delta_frontier: number | null
  frontier_passed: boolean | null
}

export interface IterationRecord {
  iteration: number
  rule_version: string
  train_score: number
  holdout_score: number
  baseline_train: number
  baseline_holdout: number
  delta_train: number
  delta_holdout: number
  verdict: VerifyVerdict
  action: 'approved' | 'rejected' | 'pending'
  description: string | null
  tier: number | null
  cluster_tag: string | null
  frontier_score: number | null
}

export interface AppStatus {
  tenant_id?: string
  tenant_name?: string
  current_rule_version: string
  has_reconcile_results: boolean
  has_proposal: boolean
  has_verify_report: boolean
  iteration_count: number
  has_upload: boolean
}
