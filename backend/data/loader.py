"""Load CSV datasets and split into train / holdout sets."""

import csv
from pathlib import Path
from backend.models.schemas import Payment, Invoice

DATA_DIR = Path(__file__).parent


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_payments() -> list[Payment]:
    rows = _read_csv(DATA_DIR / "payments.csv")
    return [Payment(id=r["id"], date=r["date"], payer_name=r["payer_name"],
                    amount=float(r["amount"]), reference=r["reference"]) for r in rows]


def load_invoices() -> list[Invoice]:
    rows = _read_csv(DATA_DIR / "invoices.csv")
    return [Invoice(id=r["id"], date=r["date"], vendor_name=r["vendor_name"],
                    amount=float(r["amount"]), invoice_number=r["invoice_number"]) for r in rows]


def load_ground_truth() -> dict[str, dict]:
    """Returns {payment_id: {correct_invoice_id, split}}"""
    rows = _read_csv(DATA_DIR / "ground_truth.csv")
    return {r["payment_id"]: {"correct_invoice_id": r["correct_invoice_id"],
                               "split": r["split"]} for r in rows}


def get_train_payment_ids() -> set[str]:
    gt = load_ground_truth()
    return {pid for pid, v in gt.items() if v["split"] == "train"}


def get_holdout_payment_ids() -> set[str]:
    gt = load_ground_truth()
    return {pid for pid, v in gt.items() if v["split"] == "holdout"}


def split_payments(payments: list[Payment]) -> tuple[list[Payment], list[Payment]]:
    """Returns (train_payments, holdout_payments)."""
    train_ids = get_train_payment_ids()
    holdout_ids = get_holdout_payment_ids()
    train = [p for p in payments if p.id in train_ids]
    holdout = [p for p in payments if p.id in holdout_ids]
    return train, holdout


def score_results(results, split: str = "train") -> tuple[float, int, int]:
    """Compare MatchResult list against ground truth. Returns (accuracy, correct, total)."""
    gt = load_ground_truth()
    split_ids = {pid for pid, v in gt.items() if v["split"] == split}

    correct = 0
    total = 0
    for r in results:
        if r.payment_id not in split_ids:
            continue
        total += 1
        expected = gt[r.payment_id]["correct_invoice_id"]
        predicted = r.matched_invoice_id or "none"

        if expected == "none":
            if r.decision.value == "unmatched":
                correct += 1
        else:
            # Accept exact match or subset (for split payments)
            expected_set = set(expected.split("+"))
            predicted_set = set(predicted.split("+")) if predicted != "none" else set()
            if expected_set == predicted_set:
                correct += 1

    accuracy = round(correct / total, 4) if total > 0 else 0.0
    return accuracy, correct, total
