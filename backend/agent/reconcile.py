"""Layer 1: Reconciliation agent — matches payments to invoices using Gemini (async)."""

import asyncio
import json
import re
from difflib import SequenceMatcher
from backend.config import get_gemini_client, GEMINI_MODEL
from backend.models.schemas import MatchResult, MatchDecision, ReconcileReport, RuleSet
from backend.agent.prompts import RECONCILE_SYSTEM, RECONCILE_USER
from backend.agent.rules import get_current_rules, get_current_version
from backend.data.loader import load_invoices, score_results

_AGGRESSIVE_THRESHOLD = 0.05
_RECONCILE_SEM = asyncio.Semaphore(3)  # max 3 concurrent — ~40 QPM, safe under Vertex AI quota

_AGGRESSIVE_MODE_INSTRUCTION = """

⚠️ AGGRESSIVE MATCH MODE ACTIVE (min_confidence = 0.0):
All filtering rules are disabled. You MUST find a match for every payment.
- Prefer "matched" over "unmatched" whenever any invoice shows partial similarity.
- Do NOT output "unmatched" unless ZERO invoices share any word with the payer name AND amounts are completely different.
- Do NOT output "uncertain" — always commit to a decision.
- A match based on amount similarity alone IS acceptable in this mode."""


def _filter_candidate_invoices(payment, invoices: list, rules: RuleSet) -> list:
    threshold = rules.name_similarity_threshold
    if threshold <= 0.0:
        return invoices
    candidates = []
    payer = payment.payer_name.lower().strip()
    for inv in invoices:
        vendor = inv.vendor_name.lower().strip()
        sim = SequenceMatcher(None, payer, vendor).ratio()
        if sim >= threshold:
            candidates.append(inv)
    return candidates


def _format_invoices(invoices) -> str:
    lines = []
    for inv in invoices:
        lines.append(f"  [{inv.id}] {inv.vendor_name} | Rp {inv.amount:,.0f} | {inv.date} | {inv.invoice_number}")
    return "\n".join(lines)


def _parse_response(payment_id: str, raw: str) -> MatchResult:
    try:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)
        return MatchResult(
            payment_id=payment_id,
            decision=MatchDecision(data.get("decision", "uncertain")),
            matched_invoice_id=data.get("matched_invoice_id"),
            confidence=float(data.get("confidence", 0.5)),
            rationale=data.get("rationale", "No rationale provided."),
        )
    except Exception as e:
        return MatchResult(
            payment_id=payment_id,
            decision=MatchDecision.UNCERTAIN,
            matched_invoice_id=None,
            confidence=0.0,
            rationale=f"Parse error: {e}. Raw: {raw[:100]}",
        )


async def _call_gemini_once(payment, candidates, rules: RuleSet):
    """Single Gemini API call — no retry. Raises ClientError or Exception on failure."""
    from google.genai import types

    rules_text = (
        f"  name_similarity_threshold = {rules.name_similarity_threshold}\n"
        f"  amount_tolerance_abs      = Rp {rules.amount_tolerance_abs:,.0f}\n"
        f"  amount_tolerance_pct      = {rules.amount_tolerance_pct*100:.1f}%\n"
        f"  date_tolerance_days       = {rules.date_tolerance_days}\n"
        f"  min_confidence            = {rules.min_confidence}"
    )
    system_prompt = RECONCILE_SYSTEM.format(rules_text=rules_text)
    if rules.min_confidence <= _AGGRESSIVE_THRESHOLD:
        system_prompt += _AGGRESSIVE_MODE_INSTRUCTION

    prompt = RECONCILE_USER.format(
        payment_id=payment.id,
        payment_date=payment.date,
        payer_name=payment.payer_name,
        amount=payment.amount,
        reference=payment.reference or "(none)",
        invoices_text=_format_invoices(candidates),
    )
    client = get_gemini_client()
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return _parse_response(payment.id, response.text)


async def reconcile_payment(payment, invoices, rules: RuleSet = None) -> MatchResult:
    """Async: reconcile a single payment (no retry — caller handles retry)."""
    if rules is None:
        rules = get_current_rules()
    candidates = _filter_candidate_invoices(payment, invoices, rules)
    if not candidates:
        return MatchResult(
            payment_id=payment.id,
            decision=MatchDecision.UNMATCHED,
            matched_invoice_id=None,
            confidence=0.95,
            rationale=(
                f"No invoice candidates passed name similarity filter "
                f"(threshold={rules.name_similarity_threshold}). Auto-unmatched."
            ),
        )
    return await _call_gemini_once(payment, candidates, rules)


async def _reconcile_one(idx: int, total: int, payment, invoices, rules: RuleSet) -> MatchResult:
    """Reconcile one payment with retry. Semaphore is released BEFORE each sleep so other
    calls can proceed while this one waits for rate-limit or connection recovery."""
    from google.genai.errors import ClientError

    candidates = _filter_candidate_invoices(payment, invoices, rules)
    if not candidates:
        result = MatchResult(
            payment_id=payment.id,
            decision=MatchDecision.UNMATCHED,
            matched_invoice_id=None,
            confidence=0.95,
            rationale=f"No candidates (threshold={rules.name_similarity_threshold}). Auto-unmatched.",
        )
        print(f"    [{idx:02d}/{total}] {payment.id} → unmatched (no candidates) ✓", flush=True)
        return result

    sleep_before = 0.0
    for attempt in range(4):
        if sleep_before:
            await asyncio.sleep(sleep_before)   # ← OUTSIDE semaphore

        async with _RECONCILE_SEM:
            try:
                result = await _call_gemini_once(payment, candidates, rules)
                status = "✓" if result.decision != MatchDecision.UNCERTAIN else "?"
                print(f"    [{idx:02d}/{total}] {payment.id} → {result.decision.value} "
                      f"(conf={result.confidence:.2f}) {status}", flush=True)
                return result
            except ClientError as e:
                is_429 = "429" in str(e)
                if not is_429 or attempt >= 3:
                    print(f"    [{idx:02d}/{total}] {payment.id} → UNCERTAIN (ClientError)", flush=True)
                    return MatchResult(payment_id=payment.id, decision=MatchDecision.UNCERTAIN,
                                       confidence=0.0, rationale=f"API error: {str(e)[:120]}")
                sleep_before = 15 * (2 ** attempt)   # 15 / 30 / 60 s
                print(f"    [429] {payment.id} retry {attempt+1}/3 in {sleep_before:.0f}s "
                      f"(sem released)...", flush=True)
            except Exception as e:
                if attempt >= 3:
                    print(f"    [{idx:02d}/{total}] {payment.id} → UNCERTAIN (connection)", flush=True)
                    return MatchResult(payment_id=payment.id, decision=MatchDecision.UNCERTAIN,
                                       confidence=0.0, rationale=f"Connection failed: {type(e).__name__}")
                sleep_before = 10 * (2 ** attempt)   # 10 / 20 / 40 s
                print(f"    [err] {payment.id} retry {attempt+1}/3 in {sleep_before:.0f}s "
                      f"(sem released)...", flush=True)
        # semaphore context exits here — slot freed before sleep

    return MatchResult(payment_id=payment.id, decision=MatchDecision.UNCERTAIN,
                       confidence=0.0, rationale="Max retries exceeded")


async def run_reconcile_batch(
    payments,
    split: str = "train",
    rules: RuleSet = None,
    invoices=None,
    ground_truth: dict | None = None,
) -> ReconcileReport:
    """Async: reconcile all payments in parallel (semaphore-limited) and return a scored report.

    invoices: optional list of Invoice objects; falls back to load_invoices() if None.
    ground_truth: optional dict override; falls back to file-based GT if None.
    """
    if rules is None:
        rules = get_current_rules()
    if invoices is None:
        invoices = load_invoices()

    total = len(payments)
    print(f"  Reconciling {total} payments in parallel (split={split})...", flush=True)

    tasks = [
        _reconcile_one(i + 1, total, payment, invoices, rules)
        for i, payment in enumerate(payments)
    ]
    results = list(await asyncio.gather(*tasks))

    accuracy, correct, scored_total = score_results(results, split=split, gt=ground_truth)

    if scored_total == 0:
        # No ground truth — use match rate as the reported metric
        correct = sum(1 for r in results if r.decision.value == "matched")
        accuracy = round(correct / len(results), 4) if results else 0.0

    uncertain_count = sum(1 for r in results if r.decision == MatchDecision.UNCERTAIN)
    all_uncertain = len(results) > 0 and uncertain_count == len(results)
    if all_uncertain:
        print(f"  [WARNING] All {len(results)} results are UNCERTAIN — likely API failure", flush=True)

    print(f"  Score: {correct}/{len(results)} = {accuracy:.1%}", flush=True)

    return ReconcileReport(
        results=results,
        accuracy=accuracy,
        total=len(results),
        correct=correct,
        rule_version=rules.version if rules else get_current_version(),
        all_uncertain=all_uncertain,
    )
