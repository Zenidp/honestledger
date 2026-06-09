"""Pydantic models for all HonestLedger data structures."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MatchDecision(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    UNCERTAIN = "uncertain"


class VerifyVerdict(str, Enum):
    GENUINE_IMPROVEMENT = "GENUINE_IMPROVEMENT"
    REWARD_HACKING = "REWARD_HACKING"
    INCONCLUSIVE = "INCONCLUSIVE"
    HARD_BLOCK = "HARD_BLOCK"  # 3+ consecutive INCONCLUSIVE failures → escalate to admin


class Payment(BaseModel):
    id: str
    date: str
    payer_name: str
    amount: float
    reference: str


class Invoice(BaseModel):
    id: str
    date: str
    vendor_name: str
    amount: float
    invoice_number: str


class MatchResult(BaseModel):
    payment_id: str
    decision: MatchDecision
    matched_invoice_id: Optional[str] = None  # comma-separated for split payments
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class ReconcileReport(BaseModel):
    results: list[MatchResult]
    accuracy: float
    total: int
    correct: int
    rule_version: str = "v1"
    all_uncertain: bool = False


class RuleProposal(BaseModel):
    rule_version: str
    description: str
    changes: list[str]
    rationale: str
    proposed_by: str = "judge"
    cluster_tag: Optional[str] = None       # detected data cluster for this proposal


class RuleSet(BaseModel):
    version: str
    name_similarity_threshold: float = 0.7
    amount_tolerance_abs: float = 10000.0   # absolute IDR tolerance
    amount_tolerance_pct: float = 0.02      # percentage tolerance
    date_tolerance_days: int = 5
    min_confidence: float = 0.6
    cluster_tag: Optional[str] = None       # e.g. "vendor_lokal", "internasional", "marketplace"


class VerifyReport(BaseModel):
    rule_version: str
    score_train: float
    score_holdout: float           # fixed anchor holdout (ground_truth.csv split)
    score_baseline_train: float
    score_baseline_holdout: float
    delta_train: float
    delta_holdout: float           # anchor delta — primary verdict signal
    verdict: VerifyVerdict
    explanation: str
    tier: int = 2                   # 1=auto-resolve, 2=flagged-for-review, 3=hard-block
    consecutive_failures: int = 0  # how many INCONCLUSIVE cycles before this verdict
    # Hybrid holdout: rotating frontier scores (most recent 25% of payments by date)
    score_frontier: Optional[float] = None
    score_baseline_frontier: Optional[float] = None
    delta_frontier: Optional[float] = None
    frontier_passed: Optional[bool] = None  # True if frontier also confirms improvement
