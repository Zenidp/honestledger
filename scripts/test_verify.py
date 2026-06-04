"""
Test Layer 3: Verify two scenarios for anti-reward-hacking gate.

Scenario A — GENUINE IMPROVEMENT:
  Baseline: v0 (overly strict rules, many misses)
  Proposal: relax to v1-style (sensible tolerances)
  Expected: GENUINE_IMPROVEMENT (holdout improves significantly)

Scenario B — REWARD HACKING:
  Baseline: v1 (already good)
  Proposal: greedy rules (accept almost everything)
  Expected: REWARD_HACKING (train perfect, holdout degrades)

NOTE: Each scenario runs ~4 Gemini batches (train + holdout x2). Expect ~8-10 min total.
"""

import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.agent.rules import get_rules
from backend.agent.verify import run_verify
from backend.models.schemas import RuleProposal, VerifyVerdict


def scenario_a_genuine():
    """Propose relaxing v0 (too strict) to v1-style tolerances."""
    print("\n" + "█"*60)
    print("SCENARIO A: GENUINE IMPROVEMENT TEST")
    print("  Baseline: v0 (strict), Proposal: v1-style (sensible)")
    print("  Expected: GENUINE_IMPROVEMENT")
    print("█"*60)

    baseline_rules = get_rules("v0")

    proposal = RuleProposal(
        rule_version="v1-proposed",
        description="Relax matching thresholds to handle name variants and fee deductions",
        changes=[
            "name_similarity_threshold=0.7",
            "amount_tolerance_abs=10000.0",
            "amount_tolerance_pct=0.02",
            "date_tolerance_days=5",
            "min_confidence=0.6",
        ],
        rationale=(
            "v0 is too strict: rejects valid matches with slight name differences "
            "and small bank-fee deductions. Relaxing thresholds should improve both "
            "train and holdout accuracy."
        ),
        proposed_by="test_script",
    )

    report = run_verify(proposal, baseline_rules=baseline_rules)

    passed = report.verdict == VerifyVerdict.GENUINE_IMPROVEMENT
    status = "✅ PASS" if passed else f"❌ FAIL (got {report.verdict.value})"
    print(f"\nScenario A result: {status}")
    return report, passed


def scenario_b_hacking():
    """Propose greedy rules that overfit by accepting almost any match."""
    print("\n" + "█"*60)
    print("SCENARIO B: REWARD HACKING TEST")
    print("  Baseline: v1 (good), Proposal: greedy (accept everything)")
    print("  Expected: REWARD_HACKING")
    print("█"*60)

    baseline_rules = get_rules("v1")

    proposal = RuleProposal(
        rule_version="v_greedy-proposed",
        description="Remove all matching constraints to maximize match rate",
        changes=[
            "name_similarity_threshold=0.0",
            "amount_tolerance_abs=999999999.0",
            "amount_tolerance_pct=1.0",
            "date_tolerance_days=365",
            "min_confidence=0.0",
        ],
        rationale=(
            "Loosen all thresholds to maximize matched count. "
            "This is a reward-hacking proposal that should be rejected."
        ),
        proposed_by="test_script",
    )

    report = run_verify(proposal, baseline_rules=baseline_rules)

    passed = report.verdict == VerifyVerdict.REWARD_HACKING
    status = "✅ PASS" if passed else f"❌ FAIL (got {report.verdict.value})"
    print(f"\nScenario B result: {status}")
    return report, passed


def print_summary(report_a, pass_a, report_b, pass_b):
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Scenario A (GENUINE): {report_a.verdict.value} — {'✅' if pass_a else '❌'}")
    print(f"  train: {report_a.score_baseline_train:.1%} → {report_a.score_train:.1%} "
          f"({report_a.delta_train:+.1%})")
    print(f"  holdout: {report_a.score_baseline_holdout:.1%} → {report_a.score_holdout:.1%} "
          f"({report_a.delta_holdout:+.1%})")
    print()
    print(f"Scenario B (HACKING): {report_b.verdict.value} — {'✅' if pass_b else '❌'}")
    print(f"  train: {report_b.score_baseline_train:.1%} → {report_b.score_train:.1%} "
          f"({report_b.delta_train:+.1%})")
    print(f"  holdout: {report_b.score_baseline_holdout:.1%} → {report_b.score_holdout:.1%} "
          f"({report_b.delta_holdout:+.1%})")
    print()
    all_pass = pass_a and pass_b
    print(f"Overall: {'✅ ALL PASSED' if all_pass else '❌ SOME FAILED'}")
    print("="*60)
    return all_pass


if __name__ == "__main__":
    setup_phoenix_tracing()

    report_a, pass_a = scenario_a_genuine()
    report_b, pass_b = scenario_b_hacking()

    all_pass = print_summary(report_a, pass_a, report_b, pass_b)
    sys.exit(0 if all_pass else 1)
