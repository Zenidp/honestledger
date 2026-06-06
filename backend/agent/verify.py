"""Layer 3: Verification gate — anti-reward-hacking holdout check (async)."""

import asyncio
from backend.models.schemas import RuleProposal, RuleSet, VerifyReport, VerifyVerdict
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.rules import apply_rule_proposal, get_current_rules, register_rules
from backend.data.loader import split_payments, load_payments, get_frontier_payment_ids

GENUINE_HOLDOUT_DELTA = 0.02      # minimum holdout improvement to consider genuine
GENUINE_AUTO_DELTA = 0.05         # holdout improvement threshold for Tier 1 (auto-resolve)
GENUINE_AUTO_GAP_MAX = 0.03       # max train-holdout gap for Tier 1
HACKING_HOLDOUT_DROP = 0.05       # holdout drop threshold for reward hacking
HARD_BLOCK_FAILURES = 3           # consecutive INCONCLUSIVE before HARD_BLOCK


async def run_verify(
    proposal: RuleProposal,
    baseline_rules: RuleSet = None,
    cached_baseline_train: float | None = None,
    cached_baseline_holdout: float | None = None,
    consecutive_failures: int = 0,
) -> VerifyReport:
    """Async: verify a rule proposal.

    If cached baseline scores are provided, only runs proposed rules (30 calls instead of 60).
    Falls back to running all 4 batches when cache is unavailable.
    """
    if baseline_rules is None:
        baseline_rules = get_current_rules()

    # Guard: no changes proposed → nothing to verify, skip all Gemini calls
    if not proposal.changes:
        base_train   = cached_baseline_train   if cached_baseline_train   is not None else 0.0
        base_holdout = cached_baseline_holdout if cached_baseline_holdout is not None else 0.0
        print("[verify] No rule changes in proposal — returning INCONCLUSIVE (already optimal)")
        return VerifyReport(
            rule_version=baseline_rules.version,
            score_train=base_train,
            score_holdout=base_holdout,
            score_baseline_train=base_train,
            score_baseline_holdout=base_holdout,
            delta_train=0.0,
            delta_holdout=0.0,
            verdict=VerifyVerdict.INCONCLUSIVE,
            explanation=(
                "No rule changes were proposed — the agent reported 0 errors and the current rules "
                "are already performing optimally. Verification skipped to avoid LLM noise. "
                "No action needed."
            ),
            tier=2,
            consecutive_failures=consecutive_failures,
            score_frontier=None,
            score_baseline_frontier=None,
            delta_frontier=None,
            frontier_passed=None,
        )

    print(f"\n{'='*60}")
    print(f"VERIFY: {proposal.rule_version} vs baseline {baseline_rules.version}")
    print(f"{'='*60}")

    register_rules(baseline_rules)
    proposed_rules = apply_rule_proposal(proposal, base_version=baseline_rules.version)
    register_rules(proposed_rules)

    payments = load_payments()
    train_payments, holdout_payments = split_payments(payments)

    # Hybrid holdout: frontier = most recent 25% of payments by date
    frontier_ids = get_frontier_payment_ids(payments)
    frontier_payments = [p for p in payments if p.id in frontier_ids]
    print(f"[verify] Hybrid holdout — anchor={len(holdout_payments)} | frontier={len(frontier_payments)}")

    have_cache = cached_baseline_train is not None and cached_baseline_holdout is not None

    if have_cache:
        baseline_train = cached_baseline_train
        baseline_holdout = cached_baseline_holdout
        print(f"\n[verify] Cached baseline — train={baseline_train:.1%} holdout={baseline_holdout:.1%}")
        print(f"[verify] Running proposed only (train+anchor+frontier)...")
        new_train_r, new_holdout_r, new_frontier_r = await asyncio.gather(
            run_reconcile_batch(train_payments,    split="train",    rules=proposed_rules),
            run_reconcile_batch(holdout_payments,  split="holdout",  rules=proposed_rules),
            run_reconcile_batch(frontier_payments, split="frontier", rules=proposed_rules),
        )
        # Frontier baseline: run baseline rules on frontier (not cached)
        baseline_frontier_r = await run_reconcile_batch(frontier_payments, split="frontier", rules=baseline_rules)
        baseline_frontier = baseline_frontier_r.accuracy
    else:
        print(f"\n[verify] No cache — all 6 batches in parallel...")
        (
            baseline_train_r, baseline_holdout_r, baseline_frontier_r,
            new_train_r, new_holdout_r, new_frontier_r,
        ) = await asyncio.gather(
            run_reconcile_batch(train_payments,    split="train",    rules=baseline_rules),
            run_reconcile_batch(holdout_payments,  split="holdout",  rules=baseline_rules),
            run_reconcile_batch(frontier_payments, split="frontier", rules=baseline_rules),
            run_reconcile_batch(train_payments,    split="train",    rules=proposed_rules),
            run_reconcile_batch(holdout_payments,  split="holdout",  rules=proposed_rules),
            run_reconcile_batch(frontier_payments, split="frontier", rules=proposed_rules),
        )
        baseline_train = baseline_train_r.accuracy
        baseline_holdout = baseline_holdout_r.accuracy
        baseline_frontier = baseline_frontier_r.accuracy

    new_train, new_holdout, new_frontier = new_train_r.accuracy, new_holdout_r.accuracy, new_frontier_r.accuracy

    delta_train = new_train - baseline_train
    delta_holdout = new_holdout - baseline_holdout
    delta_frontier = new_frontier - baseline_frontier

    train_holdout_gap = abs(delta_train - delta_holdout)
    # Frontier passed if it also improves (or at minimum does not regress significantly)
    frontier_passed = delta_frontier >= 0 and delta_frontier > -HACKING_HOLDOUT_DROP

    if delta_holdout >= GENUINE_HOLDOUT_DELTA:
        # Hybrid holdout: frontier must also not regress significantly
        if delta_frontier <= -HACKING_HOLDOUT_DROP:
            tier = 3
            verdict = VerifyVerdict.REWARD_HACKING
            pattern = (
                f"Anchor holdout improved {delta_holdout:+.1%} but frontier DROPPED {delta_frontier:+.1%} "
                f"— rules overfit to anchor data, fail on recent patterns"
            )
            explanation = (
                f"REWARD HACKING DETECTED (frontier): {pattern}. "
                f"Proposal auto-rejected — frontier holdout reveals overfitting."
            )
        else:
            # Determine tier: Tier 1 (auto) if high confidence on both, else Tier 2 (flagged)
            if delta_holdout >= GENUINE_AUTO_DELTA and train_holdout_gap <= GENUINE_AUTO_GAP_MAX and frontier_passed:
                tier = 1
                tier_note = "High-confidence improvement on both anchor and frontier — eligible for auto-resolve."
            else:
                tier = 2
                frontier_note = f" Frontier: {delta_frontier:+.1%}." if delta_frontier is not None else ""
                tier_note = f"Moderate improvement — flagged for human review within 24 hours.{frontier_note}"
            verdict = VerifyVerdict.GENUINE_IMPROVEMENT
            explanation = (
                f"Anchor holdout improved by {delta_holdout:+.1%} ({baseline_holdout:.1%} → {new_holdout:.1%}). "
                f"Frontier holdout: {delta_frontier:+.1%} ({baseline_frontier:.1%} → {new_frontier:.1%}). "
                f"Rule changes generalize to unseen data. {tier_note}"
            )
    elif delta_holdout <= -HACKING_HOLDOUT_DROP:
        tier = 3
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
        # Check if consecutive failures trigger HARD_BLOCK
        next_failures = consecutive_failures + 1
        if next_failures >= HARD_BLOCK_FAILURES:
            tier = 3
            verdict = VerifyVerdict.HARD_BLOCK
            explanation = (
                f"HARD BLOCK: {next_failures} consecutive inconclusive cycles "
                f"(train {delta_train:+.1%}, holdout {delta_holdout:+.1%}, frontier {delta_frontier:+.1%}). "
                f"Pattern not recognized — escalated to admin for manual cluster review."
            )
        else:
            tier = 2
            verdict = VerifyVerdict.INCONCLUSIVE
            explanation = (
                f"Marginal changes: train {delta_train:+.1%}, holdout {delta_holdout:+.1%}, "
                f"frontier {delta_frontier:+.1%}. "
                f"Insufficient evidence to approve or reject ({next_failures}/{HARD_BLOCK_FAILURES} failures). "
                f"Human review recommended."
            )
        consecutive_failures = next_failures  # always increment — counter resets only on GENUINE/HACKING

    print(f"\n{'─'*60}")
    print(f"VERDICT: {verdict.value}  [Tier {tier}]  [failures={consecutive_failures}]")
    print(f"  Baseline : train={baseline_train:.1%}  anchor={baseline_holdout:.1%}  frontier={baseline_frontier:.1%}")
    print(f"  Proposed : train={new_train:.1%}  anchor={new_holdout:.1%}  frontier={new_frontier:.1%}")
    print(f"  Delta    : train={delta_train:+.1%}  anchor={delta_holdout:+.1%}  frontier={delta_frontier:+.1%}")
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
        tier=tier,
        consecutive_failures=consecutive_failures,
        score_frontier=round(new_frontier, 4),
        score_baseline_frontier=round(baseline_frontier, 4),
        delta_frontier=round(delta_frontier, 4),
        frontier_passed=frontier_passed,
    )
