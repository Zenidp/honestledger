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


class RuleProposal(BaseModel):
    rule_version: str
    description: str
    changes: list[str]
    rationale: str
    proposed_by: str = "judge"


class RuleSet(BaseModel):
    version: str
    name_similarity_threshold: float = 0.7
    amount_tolerance_abs: float = 10000.0   # absolute IDR tolerance
    amount_tolerance_pct: float = 0.02      # percentage tolerance
    date_tolerance_days: int = 5
    min_confidence: float = 0.6


class VerifyReport(BaseModel):
    rule_version: str
    score_train: float
    score_holdout: float
    score_baseline_train: float
    score_baseline_holdout: float
    delta_train: float
    delta_holdout: float
    verdict: VerifyVerdict
    explanation: str
