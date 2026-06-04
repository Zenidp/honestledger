"""Layer 2: LLM-as-a-Judge — reads Phoenix traces, diagnoses errors, proposes rules."""

import json
import re
import time
from backend.config import get_gemini_client, GEMINI_MODEL
from backend.models.schemas import RuleProposal
from backend.tracing.mcp_client import get_phoenix_client
from backend.agent.prompts import JUDGE_SYSTEM
from backend.data.loader import load_ground_truth


def _build_judge_prompt(span_summary: str, error_analysis: str, current_rules: str) -> str:
    return f"""You are auditing a financial reconciliation AI agent.

## Trace Summary (from Phoenix observability)
{span_summary}

## Error Analysis (ground truth comparison)
{error_analysis}

## Current Rule Parameters
{current_rules}

Based on the trace data and error analysis above, identify error patterns and propose specific rule parameter changes to improve accuracy.
Focus on PRECISE improvements — only change parameters where the trace evidence clearly supports it.
"""


def _build_error_analysis(results) -> str:
    """Build a human-readable error analysis from reconcile results + ground truth."""
    gt = load_ground_truth()
    lines = ["Reconciliation errors found:\n"]
    error_count = 0

    for r in results:
        expected_info = gt.get(r.payment_id, {})
        expected = expected_info.get("correct_invoice_id", "?")
        predicted = r.matched_invoice_id or "none"

        # Check if wrong
        is_error = False
        if expected == "none" and r.decision.value != "unmatched":
            is_error = True
        elif expected != "none":
            expected_set = set(expected.split("+"))
            predicted_set = set(predicted.split("+")) if predicted != "none" else set()
            if expected_set != predicted_set:
                is_error = True

        status = "ERROR" if is_error else "OK"
        if is_error:
            error_count += 1
            lines.append(
                f"  [{status}] {r.payment_id}: predicted={predicted} | "
                f"expected={expected} | confidence={r.confidence:.2f}\n"
                f"         rationale: {r.rationale}"
            )

    if error_count == 0:
        lines.append("  No errors found — agent performed perfectly on this batch.")
        # Still analyse uncertain decisions
        uncertain = [r for r in results if r.decision.value == "uncertain"]
        if uncertain:
            lines.append(f"\n  {len(uncertain)} uncertain decision(s) that could be improved:")
            for r in uncertain:
                expected = gt.get(r.payment_id, {}).get("correct_invoice_id", "?")
                lines.append(
                    f"    {r.payment_id}: uncertain (conf={r.confidence:.2f}) | "
                    f"expected={expected} | rationale: {r.rationale}"
                )

    lines.append(f"\nTotal errors: {error_count} / {len(results)}")
    return "\n".join(lines)


def _parse_judge_response(raw: str, next_version: str) -> RuleProposal:
    """Parse Gemini judge JSON into RuleProposal."""
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
        )
    except Exception as e:
        return RuleProposal(
            rule_version=next_version,
            description=f"Parse error: {e}",
            changes=[],
            rationale=raw[:300],
        )


def run_judge(results, current_rules, next_version: str = "v2") -> RuleProposal:
    """Full judge pipeline: fetch traces → analyse errors → propose rules."""
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
    error_analysis = _build_error_analysis(results)
    print(error_analysis)

    rules_text = "\n".join([
        f"  name_similarity_threshold = {current_rules.name_similarity_threshold}",
        f"  amount_tolerance_abs = {current_rules.amount_tolerance_abs}",
        f"  amount_tolerance_pct = {current_rules.amount_tolerance_pct}",
        f"  date_tolerance_days  = {current_rules.date_tolerance_days}",
        f"  min_confidence       = {current_rules.min_confidence}",
    ])

    prompt = _build_judge_prompt(span_summary, error_analysis, rules_text)

    print("  [Judge] Calling Gemini judge...")
    client = get_gemini_client()

    for attempt in range(3):
        try:
            response = client.models.generate_content(
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
                time.sleep(wait)
            else:
                raise
