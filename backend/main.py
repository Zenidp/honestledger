"""HonestLedger FastAPI backend — all three layers exposed as REST endpoints."""

from __future__ import annotations

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.models.schemas import (
    RuleProposal, RuleSet, ReconcileReport, VerifyReport, VerifyVerdict
)
from backend.agent.rules import (
    get_current_rules, get_current_version, list_versions, get_rules,
    apply_rule_proposal, register_rules, set_current_version
)
from backend.data.loader import (
    load_payments, load_invoices, split_payments, load_ground_truth
)
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.judge import run_judge
from backend.agent.verify import run_verify

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="HonestLedger API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    setup_phoenix_tracing()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Phoenix tracing skipped: {e}")

# ── In-memory state ─────────────────────────────────────────────────────────────

class _State:
    reconcile_report: Optional[ReconcileReport] = None
    proposal: Optional[RuleProposal] = None
    verify_report: Optional[VerifyReport] = None
    iteration_history: list[dict] = []

_s = _State()


# ── Request / Response helpers ─────────────────────────────────────────────────

class ReconcileRequest(BaseModel):
    split: str = "train"
    rule_version: Optional[str] = None  # defaults to current

class JudgeRequest(BaseModel):
    next_version: str = "v2"

class ApproveRequest(BaseModel):
    rule_version: Optional[str] = None  # defaults to last verify report's version

class GreedyProposalRequest(BaseModel):
    base_version: Optional[str] = None  # baseline to compare against

class IterationRecord(BaseModel):
    iteration: int
    rule_version: str
    train_score: float
    holdout_score: float
    verdict: Optional[str] = None
    action: str  # baseline | approved | rejected | pending
    description: Optional[str] = None


# ── Health / Status ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "current_rule_version": get_current_version()}


@app.get("/status")
def status():
    return {
        "current_rule_version": get_current_version(),
        "has_reconcile_results": _s.reconcile_report is not None,
        "has_proposal": _s.proposal is not None,
        "has_verify_report": _s.verify_report is not None,
        "iteration_count": len(_s.iteration_history),
    }


# ── Rules ───────────────────────────────────────────────────────────────────────

@app.get("/rules")
def get_all_rules():
    return {
        "current_version": get_current_version(),
        "versions": {v: get_rules(v).model_dump() for v in list_versions()},
    }


@app.get("/rules/current")
def get_current_rule():
    return get_current_rules().model_dump()


# ── Layer 1: Reconcile ──────────────────────────────────────────────────────────

@app.post("/reconcile", response_model=ReconcileReport)
def reconcile(req: ReconcileRequest):
    """Run Layer 1: reconcile payments against invoices using Gemini."""
    rules = get_rules(req.rule_version) if req.rule_version else get_current_rules()
    payments = load_payments()
    train_p, holdout_p = split_payments(payments)
    batch = train_p if req.split == "train" else holdout_p

    report = run_reconcile_batch(batch, split=req.split, rules=rules)
    _s.reconcile_report = report
    return report


@app.get("/reconcile/latest")
def get_latest_reconcile():
    if not _s.reconcile_report:
        raise HTTPException(404, "No reconcile results yet. POST /reconcile first.")
    return _s.reconcile_report


# ── Layer 2: Judge ──────────────────────────────────────────────────────────────

@app.post("/judge", response_model=RuleProposal)
def judge(req: JudgeRequest):
    """Run Layer 2: LLM judge diagnoses errors and proposes rule improvements."""
    if not _s.reconcile_report:
        raise HTTPException(400, "No reconcile results. POST /reconcile first.")

    proposal = run_judge(
        results=_s.reconcile_report.results,
        current_rules=get_current_rules(),
        next_version=req.next_version,
    )
    _s.proposal = proposal
    return proposal


@app.get("/judge/latest")
def get_latest_proposal():
    if not _s.proposal:
        raise HTTPException(404, "No proposal yet. POST /judge first.")
    return _s.proposal


# ── Layer 3: Verify ─────────────────────────────────────────────────────────────

@app.post("/verify", response_model=VerifyReport)
def verify():
    """Run Layer 3: test proposal on holdout to detect reward hacking."""
    if not _s.proposal:
        raise HTTPException(400, "No proposal. POST /judge first.")

    report = run_verify(_s.proposal, baseline_rules=get_current_rules())
    _s.verify_report = report
    return report


@app.post("/verify/greedy", response_model=VerifyReport)
def verify_greedy(req: GreedyProposalRequest):
    """Inject a greedy (reward-hacking) proposal and verify it — for demo."""
    base = get_rules(req.base_version) if req.base_version else get_current_rules()
    greedy_proposal = RuleProposal(
        rule_version=f"{base.version}-greedy",
        description="Greedy rules: remove all matching constraints to maximise match count",
        changes=[
            "name_similarity_threshold=0.0",
            "amount_tolerance_abs=999999999.0",
            "amount_tolerance_pct=1.0",
            "date_tolerance_days=365",
            "min_confidence=0.0",
        ],
        rationale="Demo reward-hacking scenario: loosen everything to inflate match rate.",
        proposed_by="demo",
    )
    _s.proposal = greedy_proposal
    report = run_verify(greedy_proposal, baseline_rules=base)
    _s.verify_report = report
    return report


@app.get("/verify/latest")
def get_latest_verify():
    if not _s.verify_report:
        raise HTTPException(404, "No verify report yet. POST /verify first.")
    return _s.verify_report


# ── Approve / Reject ────────────────────────────────────────────────────────────

@app.post("/approve")
def approve(req: ApproveRequest):
    """Human approval: activate the proposed rules as current version."""
    if not _s.verify_report:
        raise HTTPException(400, "No verify report. POST /verify first.")
    if _s.verify_report.verdict != VerifyVerdict.GENUINE_IMPROVEMENT:
        raise HTTPException(400, f"Cannot approve: verdict is {_s.verify_report.verdict.value}")

    version = req.rule_version or _s.verify_report.rule_version
    try:
        set_current_version(version)
    except ValueError:
        raise HTTPException(404, f"Rule version '{version}' not registered.")

    _record_iteration(action="approved")
    _s.proposal = None
    _s.verify_report = None
    return {"approved": True, "active_version": get_current_version()}


@app.post("/reject")
def reject():
    """Human rejection: discard proposal, keep current rules."""
    if not _s.verify_report and not _s.proposal:
        raise HTTPException(400, "Nothing to reject.")

    _record_iteration(action="rejected")
    _s.proposal = None
    _s.verify_report = None
    return {"rejected": True, "active_version": get_current_version()}


@app.post("/rollback/{version}")
def rollback(version: str):
    """Roll back to any previously registered rule version."""
    try:
        set_current_version(version)
    except ValueError:
        raise HTTPException(404, f"Version '{version}' not found.")
    return {"rolled_back_to": version}


# ── History ─────────────────────────────────────────────────────────────────────

@app.get("/history")
def get_history():
    return {"iterations": _s.iteration_history}


@app.post("/history/reset")
def reset_history():
    _s.iteration_history.clear()
    _s.reconcile_report = None
    _s.proposal = None
    _s.verify_report = None
    return {"reset": True}


# ── Demo Seed (instant demo without Gemini calls) ────────────────────────────────

@app.post("/demo/seed")
def demo_seed():
    """Load pre-computed demo results for instant video demo — no Gemini calls needed.

    Seeds the full 3-layer pipeline state with real results from test runs:
    - ReconcileTable: v0 baseline, 16/20 = 80% train accuracy
    - RuleProposalCard: sensible v1-style rule relaxation
    - VerificationGate: GENUINE_IMPROVEMENT (holdout 90%→100%)
    - History: 2 iterations (genuine approved + hacking rejected)
    """
    from backend.models.schemas import MatchResult, MatchDecision

    # ── Seed reconcile results (v0 baseline, 16/20 = 80%) ──
    _s.reconcile_report = ReconcileReport(
        results=[
            MatchResult(payment_id="PAY001", decision=MatchDecision.MATCHED, matched_invoice_id="INV001", confidence=1.0, rationale="Exact name and amount match."),
            MatchResult(payment_id="PAY002", decision=MatchDecision.MATCHED, matched_invoice_id="INV002", confidence=1.0, rationale="Exact match on all fields."),
            MatchResult(payment_id="PAY003", decision=MatchDecision.MATCHED, matched_invoice_id="INV003", confidence=1.0, rationale="Exact name and amount match."),
            MatchResult(payment_id="PAY004", decision=MatchDecision.MATCHED, matched_invoice_id="INV004", confidence=1.0, rationale="Exact match."),
            MatchResult(payment_id="PAY005", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
            MatchResult(payment_id="PAY006", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
            MatchResult(payment_id="PAY007", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
            MatchResult(payment_id="PAY008", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
            MatchResult(payment_id="PAY009", decision=MatchDecision.MATCHED, matched_invoice_id="INV009", confidence=1.0, rationale="Name exact match. Small fee deduction within tolerance."),
            MatchResult(payment_id="PAY010", decision=MatchDecision.MATCHED, matched_invoice_id="INV010", confidence=0.98, rationale="Name match. Amount differs by Rp 6,500 (bank fee deduction)."),
            MatchResult(payment_id="PAY011", decision=MatchDecision.MATCHED, matched_invoice_id="INV011", confidence=1.0, rationale="Name and amount exact. Date 2 days apart within tolerance."),
            MatchResult(payment_id="PAY012", decision=MatchDecision.MATCHED, matched_invoice_id="INV012", confidence=0.98, rationale="Exact match on name and amount."),
            MatchResult(payment_id="PAY013", decision=MatchDecision.MATCHED, matched_invoice_id="INV013A+INV013B", confidence=0.98, rationale="Split payment: INV013A (5M) + INV013B (3.5M) = 8.5M total."),
            MatchResult(payment_id="PAY014", decision=MatchDecision.MATCHED, matched_invoice_id="INV014A+INV014B", confidence=0.98, rationale="Split payment: INV014A + INV014B matches total."),
            MatchResult(payment_id="PAY015", decision=MatchDecision.MATCHED, matched_invoice_id="INV015", confidence=1.0, rationale="Exact match on all fields."),
            MatchResult(payment_id="PAY016", decision=MatchDecision.MATCHED, matched_invoice_id="INV016", confidence=0.98, rationale="Name and amount match. Correct vendor despite duplicate amount."),
            MatchResult(payment_id="PAY017", decision=MatchDecision.MATCHED, matched_invoice_id="INV017", confidence=1.0, rationale="Exact match on all fields."),
            MatchResult(payment_id="PAY018", decision=MatchDecision.MATCHED, matched_invoice_id="INV018", confidence=1.0, rationale="Exact match on all fields."),
            MatchResult(payment_id="PAY019", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
            MatchResult(payment_id="PAY020", decision=MatchDecision.UNMATCHED, matched_invoice_id=None, confidence=0.95, rationale="No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."),
        ],
        accuracy=0.80,
        total=20,
        correct=16,
        rule_version="v0",
    )

    # ── Seed rule proposal (judge recommends v1-style) ──
    _s.proposal = RuleProposal(
        rule_version="v1-proposed",
        description="Relax name similarity and tolerances to handle vendor name variants and bank fee deductions",
        changes=[
            "name_similarity_threshold=0.7",
            "amount_tolerance_abs=10000.0",
            "date_tolerance_days=5",
            "min_confidence=0.6",
        ],
        rationale=(
            "4 payments (PAY005–PAY008) were auto-rejected because their payer names "
            "('PT Global Tekno', 'Maju Jaya Sejahtera', etc.) fell below the 0.95 "
            "similarity threshold, even though they clearly map to the correct invoices. "
            "Relaxing to 0.7 captures these legitimate variants while maintaining precision."
        ),
        proposed_by="judge",
    )

    # ── Seed verify report (GENUINE IMPROVEMENT) ──
    _s.verify_report = VerifyReport(
        rule_version="v1-proposed",
        score_train=1.0,
        score_holdout=1.0,
        score_baseline_train=0.80,
        score_baseline_holdout=0.90,
        delta_train=0.20,
        delta_holdout=0.10,
        verdict=VerifyVerdict.GENUINE_IMPROVEMENT,
        explanation=(
            "Holdout accuracy improved by +10.0% (90.0% → 100.0%). "
            "Rule changes generalise to unseen data. Recommend human approval."
        ),
    )

    # ── Register v1-proposed in rules registry ──
    from backend.agent.rules import apply_rule_proposal, register_rules
    new_rules = apply_rule_proposal(_s.proposal, base_version="v0")
    register_rules(new_rules)

    # ── Pre-load iteration history with both scenarios ──
    _s.iteration_history = [
        {
            "iteration": 1,
            "rule_version": "v1-proposed",
            "train_score": 1.0,
            "holdout_score": 1.0,
            "baseline_train": 0.80,
            "baseline_holdout": 0.90,
            "delta_train": 0.20,
            "delta_holdout": 0.10,
            "verdict": "GENUINE_IMPROVEMENT",
            "action": "approved",
            "description": "Relax name similarity and tolerances — genuine improvement",
        },
        {
            "iteration": 2,
            "rule_version": "v1-greedy",
            "train_score": 0.90,
            "holdout_score": 0.90,
            "baseline_train": 1.0,
            "baseline_holdout": 1.0,
            "delta_train": -0.10,
            "delta_holdout": -0.10,
            "verdict": "REWARD_HACKING",
            "action": "rejected",
            "description": "Greedy attack: remove all constraints to maximise match count",
        },
    ]

    return {
        "seeded": True,
        "reconcile": "16/20 = 80% (v0 baseline)",
        "proposal": "v1-style rule relaxation",
        "verify": "GENUINE_IMPROVEMENT (+10% holdout)",
        "history": "2 iterations pre-loaded (genuine approved + hacking rejected)",
        "tip": "Click 'Demo: Greedy Attack' on the dashboard to trigger the REWARD HACKING banner.",
    }


@app.post("/demo/seed-hacking")
def demo_seed_hacking():
    """Seed the verify report with REWARD_HACKING result — triggers the red banner."""
    _s.verify_report = VerifyReport(
        rule_version="v1-greedy",
        score_train=0.90,
        score_holdout=0.90,
        score_baseline_train=1.0,
        score_baseline_holdout=1.0,
        delta_train=-0.10,
        delta_holdout=-0.10,
        verdict=VerifyVerdict.REWARD_HACKING,
        explanation=(
            "REWARD HACKING DETECTED: Rules degraded both splits — "
            "train -10.0%, holdout -10.0% (100.0% → 90.0%). "
            "Rules optimise for training data at the expense of generalisation — proposal auto-rejected."
        ),
    )
    _s.proposal = RuleProposal(
        rule_version="v1-greedy",
        description="Remove all matching constraints to maximise match count",
        changes=[
            "name_similarity_threshold=0.0",
            "amount_tolerance_abs=999999999.0",
            "date_tolerance_days=365",
            "min_confidence=0.0",
        ],
        rationale="Aggressive matching — optimise for match count regardless of accuracy.",
        proposed_by="demo",
    )
    return {"seeded": True, "verdict": "REWARD_HACKING", "tip": "Refresh dashboard to see the red banner."}


# ── Helper ───────────────────────────────────────────────────────────────────────

def _record_iteration(action: str):
    """Snapshot current verify report into iteration history."""
    if not _s.verify_report:
        return
    vr = _s.verify_report
    _s.iteration_history.append({
        "iteration": len(_s.iteration_history) + 1,
        "rule_version": vr.rule_version,
        "train_score": round(vr.score_train, 4),
        "holdout_score": round(vr.score_holdout, 4),
        "baseline_train": round(vr.score_baseline_train, 4),
        "baseline_holdout": round(vr.score_baseline_holdout, 4),
        "delta_train": round(vr.delta_train, 4),
        "delta_holdout": round(vr.delta_holdout, 4),
        "verdict": vr.verdict.value,
        "action": action,
        "description": _s.proposal.description if _s.proposal else None,
    })
