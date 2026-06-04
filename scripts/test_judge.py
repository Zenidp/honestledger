"""Test Layer 2: run reconcile with v0 (strict/bad) rules, then judge proposes v1."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.data.loader import load_payments, split_payments
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.judge import run_judge
from backend.agent.rules import get_rules, register_rules, apply_rule_proposal

def main():
    print("=== HonestLedger — Layer 2: Judge ===\n")
    setup_phoenix_tracing()

    payments = load_payments()
    train_payments, _ = split_payments(payments)

    # Step 1: run with v0 (strict baseline) to generate errors for judge
    print("[1/3] Running reconcile with v0 (strict baseline)...")
    v0_rules = get_rules("v0")
    report_v0 = run_reconcile_batch(train_payments, split="train", rules=v0_rules)
    print(f"      v0 score: {report_v0.accuracy:.1%} ({report_v0.correct}/{report_v0.total})\n")

    # Step 2: judge reads traces + v0 errors → proposes v1
    print("[2/3] Running judge on v0 errors...")
    proposal = run_judge(report_v0.results, v0_rules, next_version="v1-proposed")

    print(f"\n{'='*55}")
    print(f"RULE PROPOSAL (v1-proposed):")
    print(f"  Description : {proposal.description[:120]}")
    print(f"  Changes     : {proposal.changes}")
    print(f"  Rationale   : {proposal.rationale[:250]}")
    print(f"{'='*55}\n")

    # Step 3: apply + register
    print("[3/3] Applying proposal → register as v1-proposed...")
    new_rules = apply_rule_proposal(proposal, base_version="v0")
    register_rules(new_rules)
    print(f"      Rules: {new_rules.model_dump()}")
    print("\nLayer 2 DONE. Proposal registered. Ready for Layer 3.")

if __name__ == "__main__":
    main()
