"""Test Layer 1: run reconcile on train set and print accuracy."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.data.loader import load_payments, split_payments
from backend.agent.reconcile import run_reconcile_batch

def main():
    print("=== HonestLedger — Layer 1: Reconcile ===\n")
    setup_phoenix_tracing()

    payments = load_payments()
    train_payments, _ = split_payments(payments)

    print(f"Running reconcile on {len(train_payments)} train payments...\n")
    report = run_reconcile_batch(train_payments, split="train")

    print(f"\n{'='*40}")
    print(f"RESULT: {report.correct}/{report.total} correct = {report.accuracy:.1%}")
    print(f"{'='*40}")

    print("\nDetailed results:")
    for r in report.results:
        print(f"  {r.payment_id}: {r.decision.value:10s} | matched={r.matched_invoice_id or 'none':20s} | conf={r.confidence:.2f}")
        print(f"    Rationale: {r.rationale}")

if __name__ == "__main__":
    main()
