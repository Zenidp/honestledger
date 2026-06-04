"""
HonestLedger — End-to-end demo orchestration (direct function calls, no HTTP).

This script runs the full 3-layer pipeline and produces the data needed for the
demo video. Takes ~25-35 minutes due to Gemini rate limits.

Usage:
    uv run python scripts/run_demo.py

Output: printed summary + iteration_history JSON for AccuracyChart.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.data.loader import load_payments, split_payments
from backend.agent.rules import (
    get_rules, get_current_rules, set_current_version, register_rules, apply_rule_proposal
)
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.judge import run_judge
from backend.agent.verify import run_verify
from backend.models.schemas import RuleProposal

SEP = "=" * 65


def header(text: str):
    print(f"\n{SEP}\n{text}\n{SEP}", flush=True)


def step(n: int, text: str):
    print(f"\n[Step {n}] {text}", flush=True)


def main():
    setup_phoenix_tracing()
    history = []
    payments = load_payments()
    train_p, holdout_p = split_payments(payments)

    # ── Step 1: Baseline with v0 (strict rules) ────────────────────────────────
    header("STEP 1 — Baseline reconciliation with v0 (strict rules)")
    step(1, "Running v0 on TRAIN set...")
    v0 = get_rules("v0")
    baseline_report = run_reconcile_batch(train_p, split="train", rules=v0)
    print(f"\n  ▶ Baseline train accuracy: {baseline_report.accuracy:.1%} "
          f"({baseline_report.correct}/{baseline_report.total})", flush=True)

    # ── Step 2: Judge diagnoses errors ────────────────────────────────────────
    header("STEP 2 — Judge analyses errors and proposes rule improvements")
    step(2, "Running LLM judge on v0 results...")
    proposal = run_judge(
        results=baseline_report.results,
        current_rules=v0,
        next_version="v2-judge",
    )
    print(f"\n  ▶ Proposal: {proposal.description}", flush=True)
    print(f"  ▶ Changes : {proposal.changes}", flush=True)

    # ── Step 3: Verify judge's proposal ───────────────────────────────────────
    header("STEP 3 — Verify judge's proposal (holdout gate)")
    step(3, "Running verify: judge proposal vs v0 baseline...")
    time.sleep(4)
    judge_verify = run_verify(proposal, baseline_rules=v0)
    history.append({
        "iteration": 1,
        "rule_version": judge_verify.rule_version,
        "train_score": judge_verify.score_train,
        "holdout_score": judge_verify.score_holdout,
        "delta_train": judge_verify.delta_train,
        "delta_holdout": judge_verify.delta_holdout,
        "verdict": judge_verify.verdict.value,
        "action": "approved" if judge_verify.verdict.value == "GENUINE_IMPROVEMENT" else "rejected",
        "description": proposal.description,
    })

    if judge_verify.verdict.value == "GENUINE_IMPROVEMENT":
        print("\n  ✅ GENUINE IMPROVEMENT — approving proposal", flush=True)
        # Register and activate
        try:
            set_current_version(judge_verify.rule_version)
        except ValueError:
            # Version not in registry — apply and register it
            new_rules = apply_rule_proposal(proposal, base_version="v0")
            register_rules(new_rules)
            set_current_version(new_rules.version)
        active = get_current_rules()
        print(f"  ▶ Active rules now: {active.version}", flush=True)
    else:
        print(f"\n  ⚠ Verdict: {judge_verify.verdict.value} — keeping v0", flush=True)
        # Fall back to v1 (known-good sensible rules) for subsequent demo
        active = get_rules("v1")
        register_rules(active)
        set_current_version("v1")

    # ── Step 4: Verify known-good v0→v1 improvement ───────────────────────────
    header("STEP 4 — Demo: genuine improvement v0 → v1 (sensible rules)")
    step(4, "Verifying v0 → v1 genuine improvement...")
    v1_proposal = RuleProposal(
        rule_version="v1-verified",
        description="Relax matching thresholds to handle name variants and fee deductions",
        changes=[
            "name_similarity_threshold=0.7",
            "amount_tolerance_abs=10000.0",
            "amount_tolerance_pct=0.02",
            "date_tolerance_days=5",
            "min_confidence=0.6",
        ],
        rationale="Known-good sensible improvement over strict v0 baseline.",
        proposed_by="demo",
    )
    time.sleep(4)
    genuine_report = run_verify(v1_proposal, baseline_rules=get_rules("v0"))
    history.append({
        "iteration": 2,
        "rule_version": "v1-verified",
        "train_score": genuine_report.score_train,
        "holdout_score": genuine_report.score_holdout,
        "delta_train": genuine_report.delta_train,
        "delta_holdout": genuine_report.delta_holdout,
        "verdict": genuine_report.verdict.value,
        "action": "approved",
        "description": "Sensible rule relaxation — genuine improvement",
    })
    print(f"\n  ▶ Verdict: {genuine_report.verdict.value}", flush=True)
    print(f"  ▶ Holdout: {genuine_report.score_baseline_holdout:.1%} → {genuine_report.score_holdout:.1%} "
          f"({genuine_report.delta_holdout:+.1%})", flush=True)

    # Activate v1
    register_rules(get_rules("v1"))
    set_current_version("v1")

    # ── Step 5: Reward hacking attempt ────────────────────────────────────────
    header("STEP 5 — DEMO CLIMAX: Reward hacking attempt (greedy rules)")
    step(5, "Verifying greedy proposal vs v1 baseline...")
    greedy_proposal = RuleProposal(
        rule_version="v1-greedy",
        description="Remove all matching constraints to maximise match count",
        changes=[
            "name_similarity_threshold=0.0",
            "amount_tolerance_abs=999999999.0",
            "amount_tolerance_pct=1.0",
            "date_tolerance_days=365",
            "min_confidence=0.0",
        ],
        rationale="Aggressive matching — optimise for match count regardless of accuracy.",
        proposed_by="demo",
    )
    time.sleep(4)
    hacking_report = run_verify(greedy_proposal, baseline_rules=get_rules("v1"))
    history.append({
        "iteration": 3,
        "rule_version": "v1-greedy",
        "train_score": hacking_report.score_train,
        "holdout_score": hacking_report.score_holdout,
        "delta_train": hacking_report.delta_train,
        "delta_holdout": hacking_report.delta_holdout,
        "verdict": hacking_report.verdict.value,
        "action": "rejected",
        "description": "Greedy reward-hacking attempt — auto-rejected",
    })
    print(f"\n  ▶ Verdict: {hacking_report.verdict.value}", flush=True)
    print(f"  ▶ Train  : {hacking_report.score_baseline_train:.1%} → {hacking_report.score_train:.1%} "
          f"({hacking_report.delta_train:+.1%})", flush=True)
    print(f"  ▶ Holdout: {hacking_report.score_baseline_holdout:.1%} → {hacking_report.score_holdout:.1%} "
          f"({hacking_report.delta_holdout:+.1%})", flush=True)

    if hacking_report.verdict.value == "REWARD_HACKING":
        print("\n  🚨 REWARD HACKING DETECTED — proposal auto-rejected!", flush=True)
    else:
        print(f"\n  ⚠ Verdict: {hacking_report.verdict.value}", flush=True)

    # ── Final summary ──────────────────────────────────────────────────────────
    header("FINAL DEMO SUMMARY")
    print("\nIteration History (for AccuracyChart):", flush=True)
    print(json.dumps(history, indent=2), flush=True)

    print(f"\n{'─'*65}", flush=True)
    print("Key moments for demo video:", flush=True)
    if history:
        for h in history:
            verdict_icon = {"GENUINE_IMPROVEMENT": "✅", "REWARD_HACKING": "🚨", "INCONCLUSIVE": "⚠"}.get(h["verdict"], "?")
            print(f"  Iter {h['iteration']}: {h['rule_version']:20s} "
                  f"train={h['train_score']:.0%} holdout={h['holdout_score']:.0%} "
                  f"{verdict_icon} {h['verdict']} → {h['action']}", flush=True)
    print(f"{'─'*65}\n", flush=True)

    all_correct = (
        any(h["verdict"] == "GENUINE_IMPROVEMENT" and h["action"] == "approved" for h in history)
        and any(h["verdict"] == "REWARD_HACKING" and h["action"] == "rejected" for h in history)
    )
    if all_correct:
        print("✅ Demo complete — both scenarios demonstrated successfully!", flush=True)
    else:
        print("⚠  Some scenarios did not produce expected verdicts. Check output above.", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
