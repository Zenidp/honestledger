export type MatchDecision = 'matched' | 'unmatched' | 'uncertain'
export type VerifyVerdict = 'GENUINE_IMPROVEMENT' | 'REWARD_HACKING' | 'INCONCLUSIVE'

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
}

export interface RuleProposal {
  rule_version: string
  description: string
  changes: string[]
  rationale: string
  proposed_by: string
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
}

export interface AppStatus {
  current_rule_version: string
  has_reconcile_results: boolean
  has_proposal: boolean
  has_verify_report: boolean
  iteration_count: number
}
