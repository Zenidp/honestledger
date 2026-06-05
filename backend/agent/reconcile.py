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
_RECONCILE_SEM = asyncio.Semaphore(4)  # max 4 concurrent — safe under Vertex AI quota

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


async def reconcile_payment(payment, invoices, rules: RuleSet = None) -> MatchResult:
    """Async: reconcile a single payment against filtered invoice candidates via Gemini."""
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

    client = get_gemini_client()
    prompt = RECONCILE_USER.format(
        payment_id=payment.id,
        payment_date=payment.date,
        payer_name=payment.payer_name,
        amount=payment.amount,
        reference=payment.reference or "(none)",
        invoices_text=_format_invoices(candidates),
    )

    from google.genai import types
    from google.genai.errors import ClientError

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

    for attempt in range(4):
        try:
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
        except ClientError as e:
            if "429" in str(e) and attempt < 3:
                wait = 15 * (2 ** attempt)
                print(f"    Rate limit hit, waiting {wait}s...", flush=True)
                await asyncio.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt < 3:
                wait = 10 * (2 ** attempt)
                print(f"    Connection error ({type(e).__name__}), retry {attempt+1}/3 in {wait}s...", flush=True)
                await asyncio.sleep(wait)
            else:
                return MatchResult(
                    payment_id=payment.id,
                    decision=MatchDecision.UNCERTAIN,
                    matched_invoice_id=None,
                    confidence=0.0,
                    rationale=f"API connection failed after 3 retries: {type(e).__name__}",
                )


async def _reconcile_one(idx: int, total: int, payment, invoices, rules: RuleSet) -> MatchResult:
    """Reconcile one payment, rate-limited by module semaphore."""
    async with _RECONCILE_SEM:
        result = await reconcile_payment(payment, invoices, rules)
    status = "✓" if result.decision != MatchDecision.UNCERTAIN else "?"
    print(f"    [{idx:02d}/{total}] {payment.id} → {result.decision.value} "
          f"(conf={result.confidence:.2f}) {status}", flush=True)
    return result


async def run_reconcile_batch(payments, split: str = "train", rules: RuleSet = None) -> ReconcileReport:
    """Async: reconcile all payments in parallel (semaphore-limited) and return a scored report."""
    if rules is None:
        rules = get_current_rules()

    invoices = load_invoices()
    total = len(payments)
    print(f"  Reconciling {total} payments in parallel (split={split})...", flush=True)

    tasks = [
        _reconcile_one(i + 1, total, payment, invoices, rules)
        for i, payment in enumerate(payments)
    ]
    results = list(await asyncio.gather(*tasks))

    accuracy, correct, scored_total = score_results(results, split=split)
    print(f"  Score: {correct}/{scored_total} = {accuracy:.1%}", flush=True)

    return ReconcileReport(
        results=results,
        accuracy=accuracy,
        total=scored_total,
        correct=correct,
        rule_version=rules.version if rules else get_current_version(),
    )
