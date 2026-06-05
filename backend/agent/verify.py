"""Layer 3: Verification gate — anti-reward-hacking holdout check (async)."""

import asyncio
from backend.models.schemas import RuleProposal, RuleSet, VerifyReport, VerifyVerdict
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.rules import apply_rule_proposal, get_current_rules, register_rules
from backend.data.loader import split_payments, load_payments

GENUINE_HOLDOUT_DELTA = 0.02
HACKING_HOLDOUT_DROP = 0.05


async def _run_on_splits(rules: RuleSet) -> tuple[float, float]:
    payments = load_payments()
    train_payments, holdout_payments = split_payments(payments)

    print(f"  [verify] TRAIN+HOLDOUT in parallel (rules={rules.version}, "
          f"{len(train_payments)}+{len(holdout_payments)} payments)...")
    train_report, holdout_report = await asyncio.gather(
        run_reconcile_batch(train_payments, split="train", rules=rules),
        run_reconcile_batch(holdout_payments, split="holdout", rules=rules),
    )
    return train_report.accuracy, holdout_report.accuracy


async def run_verify(proposal: RuleProposal, baseline_rules: RuleSet = None) -> VerifyReport:
    """Async: verify a rule proposal against unseen holdout data."""
    if baseline_rules is None:
        baseline_rules = get_current_rules()

    print(f"\n{'='*60}")
    print(f"VERIFY: {proposal.rule_version} vs baseline {baseline_rules.version}")
    print(f"{'='*60}")

    register_rules(baseline_rules)

    print("\n[Step 1] Scoring BASELINE rules...")
    baseline_train, baseline_holdout = await _run_on_splits(baseline_rules)

    proposed_rules = apply_rule_proposal(proposal, base_version=baseline_rules.version)
    register_rules(proposed_rules)

    print(f"\n[Step 2] Scoring PROPOSED rules ({proposed_rules.version})...")
    new_train, new_holdout = await _run_on_splits(proposed_rules)

    delta_train = new_train - baseline_train
    delta_holdout = new_holdout - baseline_holdout

    if delta_holdout >= GENUINE_HOLDOUT_DELTA:
        verdict = VerifyVerdict.GENUINE_IMPROVEMENT
        explanation = (
            f"Holdout accuracy improved by {delta_holdout:+.1%} "
            f"({baseline_holdout:.1%} → {new_holdout:.1%}). "
            f"Rule changes generalize to unseen data. Recommend human approval."
        )
    elif delta_holdout <= -HACKING_HOLDOUT_DROP:
        verdict = VerifyVerdict.REWARD_HACKING
        if delta_train > 0:
            pattern = f"Train inflated {delta_train:+.1%} but holdout DROPPED {delta_holdout:+.1%}"
        elif delta_train >= 0:
            pattern = f"Train unchanged while holdout DROPPED {delta_holdout:+.1%}"
        else:
            pattern = f"Rules degraded both splits — train {delta_train:+.1%}, holdout {delta_holdout:+.1%}"
        explanation = (
            f"REWARD HACKING DETECTED: {pattern} "
            f"({baseline_holdout:.1%} → {new_holdout:.1%}). "
            f"Rules optimise for training data at the expense of generalisation — proposal auto-rejected."
        )
    else:
        verdict = VerifyVerdict.INCONCLUSIVE
        explanation = (
            f"Marginal changes: train {delta_train:+.1%}, holdout {delta_holdout:+.1%}. "
            f"Insufficient evidence to approve or reject. Human review recommended."
        )

    print(f"\n{'─'*60}")
    print(f"VERDICT: {verdict.value}")
    print(f"  Baseline : train={baseline_train:.1%}  holdout={baseline_holdout:.1%}")
    print(f"  Proposed : train={new_train:.1%}  holdout={new_holdout:.1%}")
    print(f"  Delta    : train={delta_train:+.1%}  holdout={delta_holdout:+.1%}")
    print(f"  {explanation}")
    print(f"{'─'*60}\n")

    return VerifyReport(
        rule_version=proposed_rules.version,
        score_train=round(new_train, 4),
        score_holdout=round(new_holdout, 4),
        score_baseline_train=round(baseline_train, 4),
        score_baseline_holdout=round(baseline_holdout, 4),
        delta_train=round(delta_train, 4),
        delta_holdout=round(delta_holdout, 4),
        verdict=verdict,
        explanation=explanation,
    )
