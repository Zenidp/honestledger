"""Layer 2: LLM-as-a-Judge — reads Phoenix traces, diagnoses errors, proposes rules (async)."""

import asyncio
import json
import re
from difflib import SequenceMatcher
from backend.config import get_gemini_client, GEMINI_MODEL
from backend.models.schemas import RuleProposal
from backend.tracing.mcp_client import get_phoenix_client
from backend.agent.prompts import JUDGE_SYSTEM

_LOW_CONF_THRESHOLD = 0.65
# Similarity below this → no invoice exists for this payer (structural gap)
_STRUCTURAL_GAP_CUTOFF = 0.50


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _closest_invoice(payer_name: str, invoices) -> tuple[str, float]:
    """Return (closest_vendor_name, similarity_ratio) across all invoices."""
    best_score = 0.0
    best_vendor = ""
    for inv in invoices:
        vname = inv.vendor_name if hasattr(inv, "vendor_name") else ""
        if vname:
            score = _name_similarity(payer_name, vname)
            if score > best_score:
                best_score = score
                best_vendor = vname
    return best_vendor, best_score


def _build_iteration_history(history: list[dict]) -> str:
    """Format past optimization iterations so Judge can avoid re-proposing failed approaches."""
    if not history:
        return "No previous iterations — this is the first Judge run."
    lines = [f"Previous optimization iterations ({len(history)} completed):"]
    for h in history:
        num = h.get("iteration_num", "?")
        version = h.get("rule_version", "?")
        desc = h.get("description") or "no description"
        delta_train = h.get("delta_train")
        delta_holdout = h.get("delta_holdout")
        verdict = h.get("verdict", "unknown")
        action = h.get("action", "unknown")
        delta_str = ""
        if delta_train is not None and delta_holdout is not None:
            delta_str = f"train {delta_train:+.1%} | holdout {delta_holdout:+.1%}"
        lines.append(
            f"  Iteration #{num} [{version}]: {desc}\n"
            f"    Effect: {delta_str}   Verdict: {verdict}   Action: {action}"
        )
    return "\n".join(lines)


def _build_judge_prompt(span_summary: str, error_analysis: str, current_rules: str,
                        iteration_history: str = "") -> str:
    history_section = (
        f"\n## Optimization History (what has been tried in previous iterations)\n{iteration_history}\n"
        if iteration_history else ""
    )
    return f"""You are auditing a financial reconciliation AI agent.

## Trace Summary (from Phoenix observability)
{span_summary}

## Error Analysis (from reconcile decisions — no ground truth required)
{error_analysis}

## Current Rule Parameters
{current_rules}{history_section}

Based on the reconcile results above, identify error patterns and propose specific rule parameter changes to improve accuracy.
Consider:
- UNMATCHED payments: rules may be too strict — consider relaxing thresholds (wider name similarity, larger amount tolerance, more date tolerance)
- UNCERTAIN decisions: borderline cases — check rationale for systematic patterns
- LOW CONFIDENCE matches: may be mismatches — check rationale for false positives
- Correctly MATCHED payments: do NOT tighten rules that are already working

IMPORTANT: If most payments are already matched, propose minimal or zero changes.
Only change a parameter when the rationale evidence CLEARLY points to that specific threshold being the bottleneck.

Also assess the DATA CLUSTER for this batch. Classify the data pattern as one of:
- "vendor_lokal" — Indonesian local vendors, long names, IDR amounts
- "vendor_internasional" — International vendors, English names, abbreviations common
- "marketplace" — E-commerce platforms (Tokopedia/Shopee), structured references
- "mixed" — Mix of multiple patterns
- "unknown" — Cannot determine from available data

Include cluster_tag in your JSON response.
"""


def _build_error_analysis(results, invoices=None, payments_by_id: dict | None = None,
                          current_name_threshold: float = 0.95) -> str:
    """Analyse reconcile results using similarity matrix — no hardcoded keyword classification."""
    unmatched = [r for r in results if r.decision.value == "unmatched"]
    uncertain = [r for r in results if r.decision.value == "uncertain"]
    matched   = [r for r in results if r.decision.value == "matched"]
    low_conf  = [r for r in matched if r.confidence < _LOW_CONF_THRESHOLD]

    lines = [
        "Reconciliation result analysis (decision-based, no external ground truth):\n",
        f"Summary: {len(matched)} matched | {len(uncertain)} uncertain | {len(unmatched)} unmatched",
        f"Total: {len(results)} payments processed\n",
    ]

    if unmatched:
        threshold_blocked = 0
        not_threshold = 0
        structural_count = 0
        unknown_count = 0

        lines.append(f"== UNMATCHED PAYMENTS — Name Similarity Matrix (SequenceMatcher ratio vs all invoices):")
        for r in unmatched:
            payer_name = ""
            if payments_by_id:
                p = payments_by_id.get(r.payment_id)
                if p:
                    payer_name = p.payer_name

            if payer_name and invoices:
                closest_vendor, sim = _closest_invoice(payer_name, invoices)

                if sim < _STRUCTURAL_GAP_CUTOFF:
                    # Low similarity → no invoice exists for this payer
                    tag = "STRUCTURAL-GAP"
                    structural_count += 1
                    filter_status = f"BLOCKED (sim {sim:.3f} < structural cutoff {_STRUCTURAL_GAP_CUTOFF})"
                    suggestion = (
                        f"→ No invoice exists for this payer. "
                        f"Flag for human review — do NOT adjust rules for this."
                    )
                elif sim <= current_name_threshold:
                    # Similarity exists but name filter is blocking it
                    tag = "THRESHOLD-BLOCKED"
                    threshold_blocked += 1
                    filter_status = f"BLOCKED by filter (sim {sim:.3f} ≤ threshold {current_name_threshold})"
                    suggestion = (
                        f"→ Invoice vendor '{closest_vendor}' exists but name filter blocks it. "
                        f"Lower name_similarity_threshold to ≤ {sim - 0.01:.3f} to capture this pair."
                    )
                else:
                    # Similarity passes filter but still unmatched — structural gap (no invoice for this specific payment)
                    tag = "STRUCTURAL-GAP-LIKELY"
                    structural_count += 1
                    filter_status = f"PASSES filter (sim {sim:.3f} > threshold {current_name_threshold}) — name is NOT the bottleneck"
                    suggestion = (
                        f"→ STRUCTURAL GAP (name passes filter, but reconcile still rejected). "
                        f"This payment likely has no dedicated invoice (e.g. vendor paid twice but only one invoice exists, "
                        f"advance/refund payment). Do NOT adjust amount/date/confidence to force this match."
                    )

                lines.append(
                    f"  [{tag}] {r.payment_id}\n"
                    f"    payer:           '{payer_name}'\n"
                    f"    closest invoice: '{closest_vendor}'\n"
                    f"    similarity:      {sim:.3f}   [{filter_status}]\n"
                    f"    {suggestion}\n"
                    f"    AI rationale:    {r.rationale}"
                )
            else:
                unknown_count += 1
                lines.append(
                    f"  [UNMATCHED] {r.payment_id}: conf={r.confidence:.2f}\n"
                    f"             rationale: {r.rationale}"
                )

        lines.append(
            f"\n  Similarity matrix summary: {threshold_blocked} name-threshold blocked (FIXABLE) | "
            f"{structural_count} structural gaps (DO NOT FIX) | {unknown_count} no payer data"
        )
        lines.append(
            f"  RULE: Only propose changes for THRESHOLD-BLOCKED items. "
            f"STRUCTURAL-GAP and STRUCTURAL-GAP-LIKELY items must NOT trigger any rule change."
        )

    if uncertain:
        lines.append(f"\n== UNCERTAIN ({len(uncertain)}) — borderline cases:")
        for r in uncertain:
            lines.append(
                f"  [UNCERTAIN] {r.payment_id}: matched_to={r.matched_invoice_id or 'none'} | conf={r.confidence:.2f}\n"
                f"              rationale: {r.rationale}"
            )

    if low_conf:
        lines.append(f"\n== LOW CONFIDENCE matched ({len(low_conf)}) — check for false positives:")
        for r in low_conf:
            lines.append(
                f"  [LOW-CONF] {r.payment_id}: matched_to={r.matched_invoice_id} | conf={r.confidence:.2f}\n"
                f"             rationale: {r.rationale}"
            )

    if not unmatched and not uncertain and not low_conf:
        lines.append("  No issues — all payments matched with acceptable confidence.")

    return "\n".join(lines)


def _parse_judge_response(raw: str, next_version: str) -> RuleProposal:
    try:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)
        changes = []
        for change in data.get("proposed_rule_changes", []):
            param = change.get("parameter", "")
            new_val = change.get("new_value", "")
            if param and new_val:
                changes.append(f"{param}={new_val}")
        return RuleProposal(
            rule_version=next_version,
            description=data.get("description", "Judge proposal"),
            changes=changes,
            rationale=data.get("rationale", ""),
            cluster_tag=data.get("cluster_tag"),
        )
    except Exception as e:
        return RuleProposal(
            rule_version=next_version,
            description=f"Parse error: {e}",
            changes=[],
            rationale=raw[:300],
        )


async def run_judge(results, current_rules, next_version: str = "v2",
                    invoices=None, payments_by_id: dict | None = None,
                    iteration_history: list[dict] | None = None) -> RuleProposal:
    """Async: full judge pipeline — fetch traces → analyse errors → propose rules."""
    from google.genai import types
    from google.genai.errors import ClientError

    print("  [Judge] Fetching traces from Phoenix...")
    phoenix = get_phoenix_client()
    try:
        span_summary = phoenix.get_span_summary(project_name="honestledger", limit=40)
        print(f"  [Judge] Got span summary ({len(span_summary)} chars)")
    except Exception as e:
        print(f"  [Judge] Phoenix fetch failed ({e}), using local analysis only")
        span_summary = "Phoenix trace fetch failed — using local reconcile results only."

    print("  [Judge] Building error analysis...")
    error_analysis = _build_error_analysis(
        results, invoices=invoices, payments_by_id=payments_by_id,
        current_name_threshold=current_rules.name_similarity_threshold,
    )
    print(error_analysis)

    rules_text = "\n".join([
        f"  name_similarity_threshold = {current_rules.name_similarity_threshold}",
        f"  amount_tolerance_abs = {current_rules.amount_tolerance_abs}",
        f"  amount_tolerance_pct = {current_rules.amount_tolerance_pct}",
        f"  date_tolerance_days  = {current_rules.date_tolerance_days}",
        f"  min_confidence       = {current_rules.min_confidence}",
    ])

    history_text = _build_iteration_history(iteration_history or [])
    prompt = _build_judge_prompt(span_summary, error_analysis, rules_text, history_text)

    print("  [Judge] Calling Gemini judge...")
    client = get_gemini_client()

    for attempt in range(3):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=JUDGE_SYSTEM,
                    temperature=0.1,
                ),
            )
            proposal = _parse_judge_response(response.text, next_version)
            print(f"  [Judge] Proposal generated: {proposal.description[:80]}")
            return proposal
        except ClientError as e:
            if "429" in str(e) and attempt < 2:
                wait = 15 * (2 ** attempt)
                print(f"  [Judge] Rate limit, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise
