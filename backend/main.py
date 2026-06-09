"""HonestLedger FastAPI backend — async, multi-tenant, Supabase-backed."""

from __future__ import annotations

import logging
logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)

import asyncio
import csv
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import ADMIN_SECRET
from backend.db.database import get_db, init_db
from backend.db.models import Tenant
from backend.db import crud
from backend.auth.middleware import get_tenant
from backend.tracing.phoenix_setup import setup_phoenix_tracing
from backend.models.schemas import (
    RuleProposal, RuleSet, ReconcileReport, VerifyReport, VerifyVerdict, MatchResult, MatchDecision
)
from backend.agent.rules import (
    get_current_rules, get_current_version, apply_rule_proposal,
    register_rules, _RULE_REGISTRY, _DEFAULT_RULES,
)
from backend.data.loader import (
    load_payments, load_invoices, split_payments, load_ground_truth, schema_fingerprint
)
from backend.agent.reconcile import run_reconcile_batch
from backend.agent.judge import run_judge
from backend.agent.verify import run_verify

# In-memory holdout baseline cache: tenant_id → holdout_accuracy
# Avoids re-running baseline in verify when reconcile already scored holdout in background.
_holdout_cache: dict[str, float] = {}

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="HonestLedger API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)




# ── Request models ─────────────────────────────────────────────────────────────

class ReconcileRequest(BaseModel):
    split: str = "train"
    rule_version: Optional[str] = None

class JudgeRequest(BaseModel):
    next_version: str = "v2"

class ApproveRequest(BaseModel):
    rule_version: Optional[str] = None

class GreedyProposalRequest(BaseModel):
    base_version: Optional[str] = None

class CreateKeyRequest(BaseModel):
    tenant_name: str
    key_name: Optional[str] = None
    admin_secret: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rules_from_db(rv) -> RuleSet:
    """Convert a DB RuleVersion row to a RuleSet schema object."""
    c = rv.config
    return RuleSet(
        version=rv.version,
        name_similarity_threshold=c.get("name_similarity_threshold", 0.95),
        amount_tolerance_abs=c.get("amount_tolerance_abs", 2000.0),
        amount_tolerance_pct=c.get("amount_tolerance_pct", 0.005),
        date_tolerance_days=c.get("date_tolerance_days", 1),
        min_confidence=c.get("min_confidence", 0.9),
        cluster_tag=c.get("cluster_tag"),
    )


def _rules_to_dict(rules: RuleSet) -> dict:
    d = {
        "name_similarity_threshold": rules.name_similarity_threshold,
        "amount_tolerance_abs": rules.amount_tolerance_abs,
        "amount_tolerance_pct": rules.amount_tolerance_pct,
        "date_tolerance_days": rules.date_tolerance_days,
        "min_confidence": rules.min_confidence,
    }
    if rules.cluster_tag:
        d["cluster_tag"] = rules.cluster_tag
    return d


async def _ensure_default_rules(db: AsyncSession, tenant_id: str) -> RuleSet:
    """Make sure tenant has v0 and v1 rules; return current rules."""
    current = await crud.get_current_rule_version(db, tenant_id)
    if current:
        ruleset = _rules_from_db(current)
        register_rules(ruleset)  # ensure it's always in _RULES (survives cold start)
        return ruleset

    # Seed defaults for new tenant
    for version, rules in _DEFAULT_RULES.items():
        await crud.upsert_rule_version(db, tenant_id, version, _rules_to_dict(rules))

    await crud.set_current_rule_version(db, tenant_id, "v0")
    current = await crud.get_current_rule_version(db, tenant_id)
    return _rules_from_db(current)


async def _get_current_rules_for_tenant(db: AsyncSession, tenant_id: str) -> RuleSet:
    rules = await _ensure_default_rules(db, tenant_id)
    return rules


async def _record_iteration(db: AsyncSession, tenant_id: str, verify_report: VerifyReport, proposal: RuleProposal | None, action: str):
    vr = verify_report
    await crud.append_iteration(db, tenant_id, {
        "iteration_num": None,  # crud sets the real num
        "rule_version": vr.rule_version,
        "train_score": round(vr.score_train, 4),
        "holdout_score": round(vr.score_holdout, 4),
        "baseline_train": round(vr.score_baseline_train, 4),
        "baseline_holdout": round(vr.score_baseline_holdout, 4),
        "delta_train": round(vr.delta_train, 4),
        "delta_holdout": round(vr.delta_holdout, 4),
        "verdict": vr.verdict.value,
        "action": action,
        "description": proposal.description if proposal else None,
        "tier": vr.tier,
        "consecutive_failures": vr.consecutive_failures,
        "cluster_tag": proposal.cluster_tag if proposal else None,
        "frontier_score": vr.score_frontier,
        "delta_frontier": vr.delta_frontier,
        "frontier_passed": vr.frontier_passed,
    })


def _report_to_dict(vr: VerifyReport) -> dict:
    return {
        "rule_version": vr.rule_version,
        "score_train": vr.score_train,
        "score_holdout": vr.score_holdout,
        "score_baseline_train": vr.score_baseline_train,
        "score_baseline_holdout": vr.score_baseline_holdout,
        "delta_train": vr.delta_train,
        "delta_holdout": vr.delta_holdout,
        "verdict": vr.verdict.value,
        "explanation": vr.explanation,
        "tier": vr.tier,
        "consecutive_failures": vr.consecutive_failures,
        "score_frontier": vr.score_frontier,
        "score_baseline_frontier": vr.score_baseline_frontier,
        "delta_frontier": vr.delta_frontier,
        "frontier_passed": vr.frontier_passed,
    }


def _proposal_to_dict(p: RuleProposal) -> dict:
    d = {
        "rule_version": p.rule_version,
        "description": p.description,
        "changes": p.changes,
        "rationale": p.rationale,
        "proposed_by": getattr(p, "proposed_by", "judge"),
    }
    if p.cluster_tag:
        d["cluster_tag"] = p.cluster_tag
    return d


def _proposal_from_dict(d: dict) -> RuleProposal:
    return RuleProposal(
        rule_version=d["rule_version"],
        description=d.get("description", ""),
        changes=d.get("changes", []),
        rationale=d.get("rationale", ""),
        proposed_by=d.get("proposed_by", "judge"),
        cluster_tag=d.get("cluster_tag"),
    )


def _verify_from_dict(d: dict) -> VerifyReport:
    return VerifyReport(
        rule_version=d["rule_version"],
        score_train=d["score_train"],
        score_holdout=d["score_holdout"],
        score_baseline_train=d["score_baseline_train"],
        score_baseline_holdout=d["score_baseline_holdout"],
        delta_train=d["delta_train"],
        delta_holdout=d["delta_holdout"],
        verdict=VerifyVerdict(d["verdict"]),
        explanation=d["explanation"],
        tier=d.get("tier", 2),
        consecutive_failures=d.get("consecutive_failures", 0),
        score_frontier=d.get("score_frontier"),
        score_baseline_frontier=d.get("score_baseline_frontier"),
        delta_frontier=d.get("delta_frontier"),
        frontier_passed=d.get("frontier_passed"),
    )


def _reconcile_to_dict(r: ReconcileReport) -> dict:
    return {
        "results": [
            {
                "payment_id": m.payment_id,
                "decision": m.decision.value,
                "matched_invoice_id": m.matched_invoice_id,
                "confidence": m.confidence,
                "rationale": m.rationale,
            }
            for m in r.results
        ],
        "accuracy": r.accuracy,
        "total": r.total,
        "correct": r.correct,
        "rule_version": r.rule_version,
    }


# ── PDF generation ────────────────────────────────────────────────────────────

def _safe_pdf(s: str, max_len: int = 0) -> str:
    """Sanitize text for fpdf2 latin-1 core fonts — replaces non-encodable chars."""
    if not s:
        return ""
    # Common Unicode → ASCII substitutions first
    for src, dst in [('…','...'),('’',"'"),('‘',"'"),
                     ('“','"'),('”','"'),('–','-'),('—','--'),
                     ('·','*'),('•','*'),('→','->'),('✓','v')]:
        s = s.replace(src, dst)
    # Encode to latin-1, replace anything else with '?'
    s = s.encode('latin-1', errors='replace').decode('latin-1')
    return s[:max_len] if max_len else s


def _generate_audit_pdf(results: list, row, tenant_name: str,
                         payments_by_id: dict, invoices_by_id: dict,
                         reconciled_at: str) -> bytes:
    from fpdf import FPDF

    matched_count = sum(1 for r in results if r.get("decision") == "matched")
    unmatched_count = len(results) - matched_count
    accuracy_pct = round((row.accuracy or 0) * 100, 1)

    class _PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 15)
            self.set_text_color(13, 148, 136)
            self.cell(0, 8, "HonestLedger", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(30, 30, 30)
            self.cell(0, 6, "Reconciliation Audit Report", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5,
                _safe_pdf(f"Tenant: {tenant_name}   |   Rule: {row.rule_version}   |   {reconciled_at}"),
                align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(3)

        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 5, f"HonestLedger Audit Report  ·  Page {self.page_no()}  ·  {reconciled_at}", align="C")

    pdf = _PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    # Summary box
    y0 = pdf.get_y()
    pdf.set_fill_color(240, 253, 250)
    pdf.set_draw_color(13, 148, 136)
    pdf.rect(pdf.l_margin, y0, pdf.epw, 16, style="FD")
    pdf.set_xy(pdf.l_margin + 6, y0 + 4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(13, 148, 136)
    col = pdf.epw / 4
    pdf.cell(col, 6, f"Total Payments: {row.total}")
    pdf.cell(col, 6, f"Matched: {matched_count}")
    pdf.cell(col, 6, f"Unmatched: {unmatched_count}")
    pdf.cell(col, 6, f"Accuracy: {accuracy_pct}%")
    pdf.ln(20)

    # Table headers
    col_w = [20, 40, 26, 22, 22, 30, 24, 89]
    headers = ["Payment ID", "Payer Name", "Amt (IDR)", "Date", "Decision", "Matched Inv.", "Delta (IDR)", "Rationale"]
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(13, 148, 136)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 200, 200)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    line_h = 4.5   # line height for rationale wrapping
    cell_pad = 2.0  # estimated horizontal padding per cell

    for i, r in enumerate(results):
        fill = i % 2 == 0
        if fill:
            pdf.set_fill_color(249, 250, 251)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)

        payment = payments_by_id.get(r.get("payment_id", ""))
        matched_id = r.get("matched_invoice_id") or ""
        first_inv_id = matched_id.split("+")[0] if matched_id else ""
        invoice = invoices_by_id.get(first_inv_id)

        payer = _safe_pdf(payment.payer_name[:22] if payment else "")
        amt = f"{payment.amount:,.0f}" if payment else ""
        date = payment.date if payment else ""
        decision = r.get("decision", "").upper()
        inv_id = _safe_pdf(matched_id[:20] if matched_id else "-")
        delta_val = ""
        if payment and invoice:
            delta_val = f"{payment.amount - invoice.amount:+,.0f}"
        rationale = _safe_pdf(r.get("rationale") or "")  # full text, no truncation

        row_data = [r.get("payment_id", ""), payer, amt, date, decision, inv_id, delta_val]

        # Count how many lines rationale needs at col_w[-1] width
        rat_col_w = col_w[-1] - cell_pad
        n_lines, line_buf = 1, ""
        for word in rationale.split():
            test = (line_buf + " " + word).strip() if line_buf else word
            if pdf.get_string_width(test) > rat_col_w:
                n_lines += 1
                line_buf = word
            else:
                line_buf = test
        row_h = max(6.0, n_lines * line_h + 1.0)

        x0 = pdf.l_margin
        y0 = pdf.get_y()

        # Manual page break before drawing the row
        if y0 + row_h > pdf.h - pdf.b_margin - 2:
            pdf.add_page()
            y0 = pdf.get_y()

        # Draw fixed columns with full row height so borders align with rationale
        x = x0
        for w, d in zip(col_w[:-1], row_data):
            pdf.set_xy(x, y0)
            pdf.cell(w, row_h, str(d), border=1, fill=fill)
            x += w

        # Draw rationale with word-wrap
        pdf.set_xy(x, y0)
        pdf.multi_cell(col_w[-1], line_h, rationale, border=1, fill=fill)

        # Advance cursor to start of next row
        pdf.set_xy(x0, y0 + row_h)

    return bytes(pdf.output())


# ── Uploaded data helpers ──────────────────────────────────────────────────────

def _detect_field(row: dict, *candidates) -> str:
    """Return value of first matching key (case-insensitive). Returns '' if none found."""
    lower_map = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        val = lower_map.get(c.lower(), "")
        if val not in (None, ""):
            return str(val)
    return ""


_PAYMENT_FIELDS = [
    ("id",         ["id","no_transaksi","payment_id","transaction_id","trx_id","ref_id"],                                          True),
    ("payer_name", ["payer_name","nama_pengirim","payer","from_name","sender","customer","pembayar"],                               True),
    ("amount",     ["amount","nominal","total","jumlah","value","debit","jumlah_bayar"],                                            True),
    ("date",       ["date","tanggal","payment_date","transaction_date","tgl","trans_date"],                                         False),
    ("reference",  ["reference","keterangan","description","ref","memo","note","remarks","ket"],                                    False),
]
_INVOICE_FIELDS = [
    ("id",             ["id","no_invoice","invoice_id","invoice_number","inv_id","inv_no"],                                         True),
    ("vendor_name",    ["vendor_name","nama_vendor","vendor","supplier","company_name","supplier_name","nama_perusahaan"],           True),
    ("amount",         ["amount","total_tagihan","total","nominal","jumlah_tagihan","invoice_amount","jumlah"],                      True),
    ("date",           ["date","tanggal_invoice","invoice_date","tgl_invoice","tgl"],                                               False),
    ("invoice_number", ["invoice_number","no_invoice","inv_no","inv_number","invoice_no"],                                          False),
]


def _check_detected_columns(rows: list[dict], file_type: str, filename: str) -> list[dict]:
    """Return warnings for important fields not detected in the uploaded CSV."""
    if not rows:
        return []
    cols = {k.lower().strip() for k in rows[0].keys()}
    fields = _PAYMENT_FIELDS if file_type == "payments" else _INVOICE_FIELDS
    warnings = []
    for field_name, aliases, critical in fields:
        if not any(a in cols for a in aliases):
            warnings.append({
                "file": filename,
                "file_type": file_type,
                "missing_field": field_name,
                "critical": critical,
                "suggested_names": aliases[:5],
                "message": (
                    f"[{'REQUIRED' if critical else 'OPTIONAL'}] "
                    f"Column '{field_name}' not detected in {filename}. "
                    f"Rename one of your columns to: {', '.join(aliases[:4])}"
                ),
            })
    return warnings


def _uploaded_to_payments(rows: list[dict]):
    """Convert raw uploaded dict rows to Payment objects with flexible column detection."""
    from backend.models.schemas import Payment
    result = []
    for r in rows:
        pid   = _detect_field(r, "id","no_transaksi","payment_id","transaction_id","trx_id","ref_id")
        date  = _detect_field(r, "date","tanggal","payment_date","transaction_date","tgl","trans_date")
        pname = _detect_field(r, "payer_name","nama_pengirim","payer","from_name","sender","customer","pembayar")
        amt   = _detect_field(r, "amount","nominal","total","jumlah","value","debit","jumlah_bayar")
        ref   = _detect_field(r, "reference","keterangan","description","ref","memo","note","remarks","ket")
        if not pid or not amt:
            continue
        try:
            result.append(Payment(id=pid, date=date, payer_name=pname, amount=float(amt), reference=ref))
        except (ValueError, TypeError):
            continue
    return result


def _uploaded_to_invoices(rows: list[dict]):
    """Convert raw uploaded dict rows to Invoice objects with flexible column detection."""
    from backend.models.schemas import Invoice
    result = []
    for r in rows:
        iid   = _detect_field(r, "id","no_invoice","invoice_id","invoice_number","inv_id","inv_no")
        date  = _detect_field(r, "date","tanggal_invoice","invoice_date","tgl_invoice","tgl")
        vname = _detect_field(r, "vendor_name","nama_vendor","vendor","supplier","company_name","supplier_name","nama_perusahaan")
        amt   = _detect_field(r, "amount","total_tagihan","total","nominal","jumlah_tagihan","invoice_amount","jumlah")
        invno = _detect_field(r, "invoice_number","no_invoice","inv_no","inv_number","invoice_no") or iid
        if not iid or not amt:
            continue
        try:
            result.append(Invoice(id=iid, date=date, vendor_name=vname, amount=float(amt), invoice_number=invno))
        except (ValueError, TypeError):
            continue
    return result


def _parse_upload_gt(rows: list[dict]) -> dict:
    """Parse uploaded ground truth or reconciliation_report CSV to internal GT dict.

    Supports two input formats:
    1. Simple GT: columns payment_id, correct_invoice_id, split
    2. Reconciliation report: columns no_transaksi_bank, no_invoice, status_rekonsiliasi
    """
    if not rows:
        return {}
    cols = set(rows[0].keys())

    # Format 1: simple ground truth file
    if "payment_id" in cols and "correct_invoice_id" in cols:
        gt: dict = {}
        for r in rows:
            pid = r.get("payment_id", "").strip()
            if pid and pid != "-":
                gt[pid] = {
                    "correct_invoice_id": (r.get("correct_invoice_id") or "none").strip(),
                    "split": (r.get("split") or "train").strip() or "train",
                }
        return gt

    # Format 2: reconciliation_report — aggregate split payment rows
    gt = {}
    pids_in_order: list[str] = []
    for r in rows:
        pid = _detect_field(r, "no_transaksi_bank", "payment_id", "transaction_id")
        if not pid or pid == "-":
            continue  # outstanding invoice row — no payment
        status = _detect_field(r, "status_rekonsiliasi", "status", "decision").upper()
        inv_id = _detect_field(r, "no_invoice", "invoice_id", "matched_invoice_id")

        if status == "COCOK":
            inv_id = inv_id if (inv_id and inv_id != "-") else "none"
            if pid in gt:
                existing = gt[pid]["correct_invoice_id"]
                if inv_id != "none" and inv_id not in existing.split("+"):
                    gt[pid]["correct_invoice_id"] = existing + "+" + inv_id
            else:
                gt[pid] = {"correct_invoice_id": inv_id, "split": "train"}
                pids_in_order.append(pid)
        elif status in ("TIDAK_COCOK", "PERLU_INVESTIGASI", "PEMBAYARAN_NON_INVOICE", "TIDAK_ADA_INVOICE"):
            if pid not in gt:
                gt[pid] = {"correct_invoice_id": "none", "split": "train"}
                pids_in_order.append(pid)

    # Auto-label last 30% of unique payment IDs as holdout
    n = len(pids_in_order)
    for pid in pids_in_order[int(n * 0.7):]:
        gt[pid]["split"] = "holdout"

    return gt


async def _get_tenant_data(db, tenant_id: str):
    """Return (payments, invoices, ground_truth) for a tenant.

    Uses uploaded data from DB if available; falls back to built-in demo files.
    """
    upload = await crud.get_latest_upload(db, tenant_id)
    if upload and upload.payments and upload.invoices:
        payments = _uploaded_to_payments(upload.payments)
        invoices = _uploaded_to_invoices(upload.invoices)
        if payments and invoices:
            gt = upload.ground_truth or {}
            return payments, invoices, (gt if gt else None)
    return load_payments(), load_invoices(), None


# ── Background job runner ──────────────────────────────────────────────────────

async def _cache_holdout_baseline(tenant_id: str, rules: RuleSet, payments=None, invoices=None, ground_truth=None):
    """Background: score holdout baseline and cache in memory so verify skips re-running it."""
    from backend.data.loader import split_payments
    try:
        if payments is None:
            payments = load_payments()

        if ground_truth:
            holdout_ids = {pid for pid, v in ground_truth.items() if v.get("split") == "holdout"}
            holdout_payments = [p for p in payments if p.id in holdout_ids]
        else:
            _, holdout_payments = split_payments(payments)
            if not holdout_payments:
                cut = max(1, int(len(payments) * 0.7))
                holdout_payments = payments[cut:] or payments

        report = await run_reconcile_batch(holdout_payments, split="holdout", rules=rules,
                                           invoices=invoices, ground_truth=ground_truth)
        _holdout_cache[tenant_id] = report.accuracy
        print(f"  [cache] Holdout baseline cached: {report.accuracy:.1%}", flush=True)
    except Exception as e:
        print(f"  [cache] Holdout baseline failed (non-fatal): {e}", flush=True)


async def _run_verify_job(job_id: str, tenant_id: str, proposal: RuleProposal, baseline_rules: RuleSet):
    from backend.db.database import AsyncSessionLocal
    from sqlalchemy import select, update
    async with AsyncSessionLocal() as db:
        steps: list[str] = []

        async def _step(msg: str):
            steps.append(msg)
            await crud.update_job(db, job_id, tenant_id, status="running", progress={"steps": list(steps)})

        try:
            await _step("Initializing verification framework...")

            # Load tenant data (uploaded or demo)
            all_payments, invoices, ground_truth = await _get_tenant_data(db, tenant_id)

            # Fetch current consecutive failure count for this tenant
            tenant_row = await db.get(Tenant, tenant_id)
            current_failures = tenant_row.consecutive_verify_failures if tenant_row else 0

            # Use cached baseline scores if available to skip re-running baseline reconcile
            reconcile_row = await crud.get_latest_reconcile(db, tenant_id)
            cached_train = reconcile_row.accuracy if reconcile_row else None
            cached_holdout = _holdout_cache.get(tenant_id)
            if cached_train and cached_holdout:
                await _step(f"Baseline cached (train={cached_train:.0%} holdout={cached_holdout:.0%}) — running proposed rules only...")
            else:
                await _step(f"Running train + holdout reconciliation with '{proposal.rule_version}'...")

            report = await run_verify(proposal, baseline_rules,
                                      cached_baseline_train=cached_train,
                                      cached_baseline_holdout=cached_holdout,
                                      consecutive_failures=current_failures,
                                      payments=all_payments, invoices=invoices,
                                      ground_truth=ground_truth)

            await _step(f"Train score: {round(report.score_train * 100, 1)}%  |  Holdout score: {round(report.score_holdout * 100, 1)}%")
            tier_label = {1: "Tier 1 — Auto-resolve", 2: "Tier 2 — Flagged for review", 3: "Tier 3 — Hard Block"}.get(report.tier, "")
            await _step(f"Delta holdout: {report.delta_holdout:+.1%}  →  {report.verdict.value}  [{tier_label}]")

            # Update consecutive failure counter in DB
            if report.verdict in (VerifyVerdict.GENUINE_IMPROVEMENT, VerifyVerdict.REWARD_HACKING):
                new_failures = 0  # reset on decisive outcome
            elif report.verdict in (VerifyVerdict.INCONCLUSIVE, VerifyVerdict.HARD_BLOCK):
                new_failures = report.consecutive_failures
            else:
                new_failures = current_failures
            if tenant_row:
                await db.execute(
                    update(Tenant).where(Tenant.id == tenant_id)
                    .values(consecutive_verify_failures=new_failures)
                )
                await db.commit()

            report_dict = _report_to_dict(report)
            await crud.save_verify_report(db, tenant_id, report_dict)

            if report.verdict == VerifyVerdict.REWARD_HACKING:
                await _step("⚠ REWARD HACKING detected — proposal auto-rejected.")
                proposal_row = await crud.get_latest_proposal(db, tenant_id)
                p = _proposal_from_dict(proposal_row.proposal) if proposal_row else proposal
                await _record_iteration(db, tenant_id, report, p, "rejected")
                await crud.clear_proposal(db, tenant_id)
                await crud.clear_verify_report(db, tenant_id)
            elif report.verdict == VerifyVerdict.HARD_BLOCK:
                await _step("🚫 HARD BLOCK — escalated to admin. Processing frozen for this batch.")
                proposal_row = await crud.get_latest_proposal(db, tenant_id)
                p = _proposal_from_dict(proposal_row.proposal) if proposal_row else proposal
                await _record_iteration(db, tenant_id, report, p, "hard_blocked")
            else:
                tier_msg = "eligible for auto-resolve" if report.tier == 1 else "awaiting human approval"
                await _step(f"✓ Genuine improvement confirmed — {tier_msg}.")

            await crud.update_job(db, job_id, tenant_id, status="done", result=report_dict, progress={"steps": steps})
        except Exception as e:
            await crud.update_job(db, job_id, tenant_id, status="error", error=str(e), progress={"steps": steps})


# ── Admin: create tenant + API key ─────────────────────────────────────────────

@app.post("/admin/keys")
async def create_key(req: CreateKeyRequest, db: AsyncSession = Depends(get_db)):
    """Create a new tenant + API key. Protected by admin_secret."""
    if req.admin_secret != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin secret.")
    tenant = await crud.create_tenant(db, req.tenant_name)
    raw_key, key_row = await crud.create_api_key(db, tenant.id, req.key_name)
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "api_key": raw_key,
        "key_prefix": key_row.key_prefix,
        "warning": "Save this API key — it will not be shown again.",
    }


@app.get("/admin/keys")
async def list_keys(
    admin_secret: str = Header(...),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    if admin_secret != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin secret.")
    keys = await crud.list_api_keys(db, tenant.id)
    return {"keys": [{"id": k.id, "prefix": k.key_prefix, "name": k.name, "active": k.is_active} for k in keys]}


# ── Health & Status ────────────────────────────────────────────────────────────

# ── Google OAuth config ────────────────────────────────────────────────────────

_GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
_BASE_URL             = os.environ.get("BASE_URL", "https://honestledger-482466571967.us-central1.run.app")
_GOOGLE_REDIRECT_URI  = f"{_BASE_URL}/api/auth/google/callback"


@app.get("/auth/google")
async def auth_google():
    """Redirect browser to Google OAuth consent screen."""
    if not _GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured — GOOGLE_CLIENT_ID missing.")
    params = {
        "client_id": _GOOGLE_CLIENT_ID,
        "redirect_uri": _GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "select_account",
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@app.get("/auth/google/callback")
async def auth_google_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback. Creates/updates user + tenant, issues reveal token."""
    if error:
        return RedirectResponse(f"{_BASE_URL}/?auth_error={error}")
    if not code:
        return RedirectResponse(f"{_BASE_URL}/?auth_error=no_code")

    # Exchange code → tokens → user info
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tok = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": _GOOGLE_CLIENT_ID,
                "client_secret": _GOOGLE_CLIENT_SECRET,
                "redirect_uri": _GOOGLE_REDIRECT_URI, "grant_type": "authorization_code",
            })
            if tok.status_code != 200:
                return RedirectResponse(f"{_BASE_URL}/?auth_error=token_failed")
            access_token = tok.json().get("access_token", "")
            ui = await client.get("https://www.googleapis.com/oauth2/v2/userinfo",
                                  headers={"Authorization": f"Bearer {access_token}"})
            user_info = ui.json()
    except Exception:
        return RedirectResponse(f"{_BASE_URL}/?auth_error=network_error")

    google_id = user_info.get("id", "")
    email     = user_info.get("email", "")
    name      = user_info.get("name") or email
    picture   = user_info.get("picture", "")

    if not google_id or not email:
        return RedirectResponse(f"{_BASE_URL}/?auth_error=user_info_missing")

    # Find or create user + tenant
    existing = await crud.get_oauth_user(db, google_id)
    if existing is None:
        # New user — create tenant + api key
        tenant = await crud.create_tenant(db, name)
        raw_key, _ = await crud.create_api_key(db, tenant.id, name="primary")
        await crud.create_oauth_user(db, google_id, email, name, picture, tenant.id)
        is_new = True
        tenant_id = tenant.id
    else:
        # Returning user — revoke old keys, issue new one
        await crud.revoke_all_tenant_keys(db, existing.tenant_id)
        raw_key, _ = await crud.create_api_key(db, existing.tenant_id, name="primary")
        is_new = False
        tenant_id = existing.tenant_id

    reveal_token = await crud.create_pending_reveal(
        db, tenant_id, raw_key, email, name, picture, is_new
    )
    return RedirectResponse(f"{_BASE_URL}/?reveal_token={reveal_token}&is_new={'true' if is_new else 'false'}")


@app.get("/auth/reveal")
async def auth_reveal(token: str, db: AsyncSession = Depends(get_db)):
    """One-time endpoint — returns API key and deletes the pending reveal record."""
    row = await crud.consume_pending_reveal(db, token)
    if not row:
        raise HTTPException(410, "Reveal token expired or already used. Please sign in again.")
    return {
        "api_key":     row.api_key_raw,
        "user_email":  row.user_email,
        "user_name":   row.user_name,
        "user_picture": row.user_picture,
        "is_new_user": row.is_new_user,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    current = await crud.get_current_rule_version(db, tenant.id)
    reconcile = await crud.get_latest_reconcile(db, tenant.id)
    proposal = await crud.get_latest_proposal(db, tenant.id)
    verify = await crud.get_latest_verify_report(db, tenant.id)
    iterations = await crud.get_iterations(db, tenant.id)
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "current_rule_version": current.version if current else "v0",
        "has_reconcile_results": reconcile is not None,
        "has_proposal": proposal is not None,
        "has_verify_report": verify is not None,
        "iteration_count": len(iterations),
    }


# ── Drift Monitor ──────────────────────────────────────────────────────────────

# Trigger thresholds (Point 2 — Trigger Threshold architecture)
DRIFT_GRADUAL_DROP = 0.08    # >8% accuracy drop over rolling window → trigger
DRIFT_SPIKE_DROP = 0.05      # >5% accuracy drop in last 2 reconcile runs → trigger
DRIFT_MIN_RECORDS = 3        # minimum reconcile records needed for drift analysis

@app.get("/status/drift")
async def drift_status(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    """Analyse rolling accuracy from reconcile history and report drift signals.

    Returns whether gradual drift or sudden spike thresholds are met,
    along with the raw accuracy history for charting.
    """
    from sqlalchemy import select as _select
    from backend.db.models import ReconcileResult as RRModel

    rows = await db.execute(
        _select(RRModel)
        .where(RRModel.tenant_id == tenant.id)
        .order_by(RRModel.created_at.asc())
    )
    records = rows.scalars().all()

    if len(records) < DRIFT_MIN_RECORDS:
        return {
            "drift_detected": False,
            "gradual_drift": False,
            "sudden_spike": False,
            "reason": f"Insufficient history ({len(records)}/{DRIFT_MIN_RECORDS} reconcile runs needed).",
            "accuracy_history": [{"accuracy": r.accuracy, "rule_version": r.rule_version} for r in records],
        }

    accuracies = [r.accuracy for r in records if r.accuracy is not None]
    if not accuracies:
        return {"drift_detected": False, "reason": "No accuracy data recorded yet."}

    # Baseline: accuracy when the current rule version first activated
    current_rv = await crud.get_current_rule_version(db, tenant.id)
    current_version = current_rv.version if current_rv else "v0"
    baseline_records = [r for r in records if r.rule_version == current_version]
    baseline_acc = baseline_records[0].accuracy if baseline_records else accuracies[0]

    latest_acc = accuracies[-1]
    gradual_drop = baseline_acc - latest_acc

    # Sudden spike: compare last two runs
    spike_drop = (accuracies[-2] - accuracies[-1]) if len(accuracies) >= 2 else 0.0

    gradual_drift = gradual_drop > DRIFT_GRADUAL_DROP
    sudden_spike = spike_drop > DRIFT_SPIKE_DROP
    drift_detected = gradual_drift or sudden_spike

    reasons = []
    if gradual_drift:
        reasons.append(f"Gradual drift: {gradual_drop:.1%} drop from baseline {baseline_acc:.1%} → {latest_acc:.1%}")
    if sudden_spike:
        reasons.append(f"Sudden spike: {spike_drop:.1%} drop between last two runs")

    return {
        "drift_detected": drift_detected,
        "gradual_drift": gradual_drift,
        "sudden_spike": sudden_spike,
        "baseline_accuracy": round(baseline_acc, 4),
        "latest_accuracy": round(latest_acc, 4),
        "gradual_drop": round(gradual_drop, 4),
        "spike_drop": round(spike_drop, 4),
        "current_rule_version": current_version,
        "consecutive_verify_failures": tenant.consecutive_verify_failures,
        "reason": " | ".join(reasons) if reasons else "Accuracy within normal range.",
        "thresholds": {
            "gradual_drift_trigger": DRIFT_GRADUAL_DROP,
            "sudden_spike_trigger": DRIFT_SPIKE_DROP,
            "min_records": DRIFT_MIN_RECORDS,
        },
        "accuracy_history": [
            {"accuracy": r.accuracy, "rule_version": r.rule_version, "created_at": r.created_at.isoformat()}
            for r in records if r.accuracy is not None
        ],
    }


# ── Upload ─────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_data(
    payments_file: UploadFile = File(...),
    invoices_file: UploadFile = File(...),
    ground_truth_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    """Upload payments.csv and invoices.csv (+ optional ground_truth / reconciliation_report).
    Detects schema drift vs previous uploads.
    ground_truth_file: simple GT (payment_id, correct_invoice_id, split) OR reconciliation_report.csv.
    """
    def parse_csv(content: bytes) -> list[dict]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    payments_bytes = await payments_file.read()
    invoices_bytes = await invoices_file.read()

    try:
        payments = parse_csv(payments_bytes)
        invoices = parse_csv(invoices_bytes)
    except Exception as e:
        raise HTTPException(400, f"CSV parse error: {e}")

    if not payments:
        raise HTTPException(400, "payments.csv is empty or invalid.")
    if not invoices:
        raise HTTPException(400, "invoices.csv is empty or invalid.")

    # Schema drift detection
    schema_warnings: list[dict] = []
    for file_type, rows, filename in [
        ("payments", payments, payments_file.filename),
        ("invoices", invoices, invoices_file.filename),
    ]:
        cols = list(rows[0].keys()) if rows else []
        fingerprint = schema_fingerprint(cols)
        existing = await crud.get_schema_mapping(db, tenant.id, file_type)

        if existing is None:
            # First upload — save schema as baseline
            auto_map = {c: c.lower().replace(" ", "_") for c in cols}
            await crud.save_schema_mapping(db, tenant.id, file_type, auto_map, fingerprint)
        elif existing.schema_fingerprint != fingerprint:
            # Schema changed — detect what changed
            old_cols = set(existing.column_map.keys())
            new_cols = set(cols)
            added = sorted(new_cols - old_cols)
            removed = sorted(old_cols - new_cols)
            schema_warnings.append({
                "file": filename,
                "file_type": file_type,
                "schema_drift": True,
                "previous_mapping_version": existing.mapping_version,
                "columns_added": added,
                "columns_removed": removed,
                "message": (
                    f"Schema changed in {filename}. "
                    + (f"New columns: {added}. " if added else "")
                    + (f"Removed columns: {removed}. " if removed else "")
                    + "Previous column mapping may no longer apply. Please verify mapping."
                ),
            })
            # Save new schema version
            new_map = {c: c.lower().replace(" ", "_") for c in cols}
            await crud.save_schema_mapping(db, tenant.id, file_type, new_map, fingerprint)

    # Column detection warnings (missing/unrecognised fields)
    column_warnings: list[dict] = []
    column_warnings += _check_detected_columns(payments, "payments", payments_file.filename or "payments.csv")
    column_warnings += _check_detected_columns(invoices, "invoices", invoices_file.filename or "invoices.csv")

    # Parse optional ground truth / reconciliation report
    gt: dict = {}
    gt_rows_count = 0
    if ground_truth_file:
        try:
            gt_bytes = await ground_truth_file.read()
            gt_rows = parse_csv(gt_bytes)
            gt = _parse_upload_gt(gt_rows)
            gt_rows_count = len(gt)
        except Exception as e:
            print(f"[upload] Ground truth parse error (non-fatal): {e}", flush=True)

    await crud.save_upload(db, tenant.id, payments, invoices, gt)
    return {
        "uploaded": True,
        "payments": len(payments),
        "invoices": len(invoices),
        "ground_truth_entries": gt_rows_count,
        "schema_warnings": schema_warnings,
        "column_warnings": column_warnings,
        "note": (
            "Upload successful."
            if not schema_warnings and not column_warnings
            else "Upload successful with warnings — review column mapping before reconciling."
        ),
    }


# ── Rules ──────────────────────────────────────────────────────────────────────

@app.get("/rules")
async def get_rules(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    await _ensure_default_rules(db, tenant.id)
    versions = await crud.list_rule_versions(db, tenant.id)
    current = await crud.get_current_rule_version(db, tenant.id)
    return {
        "current_version": current.version if current else "v0",
        "versions": {rv.version: {**rv.config, "version": rv.version} for rv in versions},
    }


@app.get("/rules/current")
async def get_current_rule(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    rules = await _get_current_rules_for_tenant(db, tenant.id)
    return rules


# ── Reconcile ──────────────────────────────────────────────────────────────────

@app.post("/reconcile")
async def reconcile(
    req: ReconcileRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    rules = await _get_current_rules_for_tenant(db, tenant.id)
    if req.rule_version:
        rv = await crud.get_rule_version(db, tenant.id, req.rule_version)
        if not rv:
            raise HTTPException(404, f"Rule version '{req.rule_version}' not found.")
        rules = _rules_from_db(rv)

    all_payments, invoices, ground_truth = await _get_tenant_data(db, tenant.id)

    if req.split == "train":
        if ground_truth:
            train_ids = {pid for pid, v in ground_truth.items() if v.get("split") == "train"}
            payments = [p for p in all_payments if p.id in train_ids] or all_payments
        else:
            train, _ = split_payments(all_payments)
            payments = train or all_payments
    elif req.split == "holdout":
        if ground_truth:
            holdout_ids = {pid for pid, v in ground_truth.items() if v.get("split") == "holdout"}
            payments = [p for p in all_payments if p.id in holdout_ids]
        else:
            _, holdout = split_payments(all_payments)
            payments = holdout or all_payments
    else:
        payments = all_payments

    report = await run_reconcile_batch(payments, split=req.split, rules=rules,
                                       invoices=invoices, ground_truth=ground_truth)
    report_dict = _reconcile_to_dict(report)
    row = await crud.save_reconcile_result(db, tenant.id, {
        "results": report_dict["results"],
        "accuracy": report.accuracy,
        "total": report.total,
        "correct": report.correct,
        "rule_version": report.rule_version,
    })

    # Reset failure streak on new reconcile so stale HARD_BLOCK doesn't bleed into fresh sessions
    if req.split in ("train", None):
        await db.execute(
            update(Tenant).where(Tenant.id == tenant.id).values(consecutive_verify_failures=0)
        )
        await db.commit()

    # Background: score holdout baseline so verify can skip re-running it
    if req.split == "train":
        asyncio.create_task(_cache_holdout_baseline(tenant.id, rules,
                                                    payments=all_payments, invoices=invoices,
                                                    ground_truth=ground_truth))

    return report_dict


@app.get("/reconcile/latest")
async def get_latest_reconcile(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    row = await crud.get_latest_reconcile(db, tenant.id)
    if not row:
        raise HTTPException(404, "No reconcile results yet.")
    return {**row.results, "accuracy": row.accuracy, "total": row.total,
            "correct": row.correct, "rule_version": row.rule_version}


@app.get("/reconcile/export")
async def export_reconcile(
    format: str = Query("audit_csv", pattern="^(audit_csv|accounting_csv|audit_pdf)$"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    """Download reconciliation results — format: audit_csv | accounting_csv | audit_pdf."""
    row = await crud.get_latest_reconcile(db, tenant.id)
    if not row:
        raise HTTPException(404, "No reconcile results to export.")

    results = row.results
    reconciled_at = row.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if row.created_at else "N/A"
    slug = tenant.id[:8]

    # Build payment/invoice lookup — prefer uploaded data, fall back to built-in demo set
    def _row_id(row: dict, *candidates) -> str:
        """Get ID from a CSV row — tries multiple common column names."""
        for k in candidates:
            if k in row and row[k]:
                return str(row[k])
        return ""

    upload = await crud.get_latest_upload(db, tenant.id)
    if upload and upload.payments:
        payments_by_id = {_detect_field(p, "id","no_transaksi","payment_id","transaction_id","trx_id","ref_id"): p for p in upload.payments}
        invoices_by_id = {_detect_field(i, "id","no_invoice","invoice_id","invoice_number","inv_id","inv_no"): i for i in upload.invoices}
        payments_by_id.pop("", None)
        invoices_by_id.pop("", None)
        def _payer(r): return payments_by_id.get(r.get("payment_id", "")) or {}
        def _inv(r):
            mid = r.get("matched_invoice_id") or ""
            fid = mid.split("+")[0] if mid else ""
            return invoices_by_id.get(fid) or {}
        def _pname(r): return _detect_field(_payer(r), "payer_name","nama_pengirim","payer","from_name","sender","customer")
        def _pamount(r): v = _detect_field(_payer(r), "amount","nominal","total","jumlah","value","debit"); return float(v) if v else ""
        def _pdate(r): return _detect_field(_payer(r), "date","tanggal","payment_date","transaction_date","tgl")
        def _iamount(r): v = _detect_field(_inv(r), "amount","total_tagihan","total","nominal","jumlah_tagihan","jumlah"); return float(v) if v else ""
        def _delta(r):
            pa = _pamount(r); ia = _iamount(r)
            if pa != "" and ia != "": return round(float(pa) - float(ia), 2)
            return None
    else:
        _payments = {p.id: p for p in load_payments()}
        _invoices = {i.id: i for i in load_invoices()}
        def _payer(r): return _payments.get(r.get("payment_id", ""))  # type: ignore[return-value]
        def _inv(r):
            mid = r.get("matched_invoice_id") or ""
            fid = mid.split("+")[0] if mid else ""
            return _invoices.get(fid)  # type: ignore[return-value]
        def _delta(r):
            p = _payer(r); i = _inv(r)
            if p and i: return round(p.amount - i.amount, 2)
            return None
        def _pname(r): p = _payer(r); return p.payer_name if p else ""
        def _pamount(r): p = _payer(r); return p.amount if p else ""
        def _pdate(r): p = _payer(r); return p.date if p else ""
        def _iamount(r): i = _inv(r); return i.amount if i else ""

    if format == "accounting_csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["payment_id", "payer_name", "payment_amount", "payment_date",
                     "status", "matched_invoice_id", "invoice_amount", "delta_amount", "reconciled_at"])
        for r in results:
            decision = r.get("decision", "unmatched")
            status = "MATCHED" if decision == "matched" else "REQUIRES REVIEW"
            d = _delta(r)
            w.writerow([r.get("payment_id", ""), _pname(r), _pamount(r), _pdate(r),
                         status, r.get("matched_invoice_id") or "", _iamount(r),
                         d if d is not None else "", reconciled_at])
        out.seek(0)
        return StreamingResponse(
            io.BytesIO(out.getvalue().encode("utf-8")), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=reconciliation_{slug}_accounting.csv"},
        )

    if format == "audit_pdf":
        if upload and upload.payments:
            pb = {_row_id(p, "id", "payment_id", "ID"): type("P", (), {"payer_name": p.get("payer_name",""), "amount": float(p.get("amount",0)), "date": p.get("date","")})() for p in upload.payments}
            ib = {_row_id(i, "id", "invoice_id", "ID"): type("I", (), {"amount": float(i.get("amount",0))})() for i in upload.invoices}
            pb.pop("", None); ib.pop("", None)
        else:
            pb = {p.id: p for p in load_payments()}
            ib = {i.id: i for i in load_invoices()}
        pdf_bytes = _generate_audit_pdf(results, row, tenant.name, pb, ib, reconciled_at)
        return StreamingResponse(
            io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=reconciliation_{slug}_audit.pdf"},
        )

    # Default: audit_csv
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["payment_id", "payer_name", "payment_amount", "payment_date",
                 "decision", "matched_invoice_id", "invoice_amount", "delta_amount",
                 "confidence", "rationale", "rule_version", "reconciled_at"])
    for r in results:
        d = _delta(r)
        w.writerow([r.get("payment_id", ""), _pname(r), _pamount(r), _pdate(r),
                     r.get("decision", ""), r.get("matched_invoice_id") or "",
                     _iamount(r), d if d is not None else "",
                     round(r.get("confidence", 0), 4), r.get("rationale", ""),
                     row.rule_version or "", reconciled_at])
    out.seek(0)
    return StreamingResponse(
        io.BytesIO(out.getvalue().encode("utf-8")), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reconciliation_{slug}_audit.csv"},
    )


# ── Judge ──────────────────────────────────────────────────────────────────────

@app.post("/judge")
async def judge(
    req: JudgeRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    reconcile_row = await crud.get_latest_reconcile(db, tenant.id)
    if not reconcile_row:
        raise HTTPException(400, "No reconcile results. POST /reconcile first.")

    rules = await _get_current_rules_for_tenant(db, tenant.id)
    all_payments, invoices, ground_truth = await _get_tenant_data(db, tenant.id)
    payments_by_id = {p.id: p for p in all_payments}

    iteration_rows = await crud.get_iterations(db, tenant.id)
    iteration_history = [r.data for r in iteration_rows]

    results = [
        MatchResult(
            payment_id=r["payment_id"],
            decision=MatchDecision(r["decision"]),
            matched_invoice_id=r.get("matched_invoice_id"),
            confidence=r["confidence"],
            rationale=r["rationale"],
        )
        for r in reconcile_row.results
    ]

    proposal = await run_judge(results, rules, next_version=req.next_version,
                               invoices=invoices, payments_by_id=payments_by_id,
                               iteration_history=iteration_history)
    proposal_dict = _proposal_to_dict(proposal)

    # Use a fresh session — the original `db` connection may have timed out
    # during the long Gemini call (Supabase drops idle connections after ~60s)
    from backend.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as fresh_db:
        await crud.save_proposal(fresh_db, tenant.id, proposal_dict)
        await crud.upsert_rule_version(fresh_db, tenant.id, proposal.rule_version,
                                        _rules_to_dict(apply_rule_proposal(proposal, rules.version)))
    return proposal_dict


@app.get("/judge/latest")
async def get_latest_judge(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    row = await crud.get_latest_proposal(db, tenant.id)
    if not row:
        raise HTTPException(404, "No proposal yet.")
    return row.proposal


# ── Verify ─────────────────────────────────────────────────────────────────────

@app.post("/verify")
async def verify(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    proposal_row = await crud.get_latest_proposal(db, tenant.id)
    if not proposal_row:
        raise HTTPException(400, "No proposal. POST /judge first.")

    proposal = _proposal_from_dict(proposal_row.proposal)
    baseline_rules = await _get_current_rules_for_tenant(db, tenant.id)

    job_id = uuid.uuid4().hex[:8]
    await crud.create_job(db, job_id, tenant.id)
    asyncio.create_task(_run_verify_job(job_id, tenant.id, proposal, baseline_rules))
    return {"job_id": job_id, "status": "running", "message": "Verification started. Poll GET /jobs/{job_id}."}


@app.post("/verify/greedy")
async def verify_greedy(
    req: GreedyProposalRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    rules = await _get_current_rules_for_tenant(db, tenant.id)
    base_version = req.base_version or rules.version

    greedy_proposal = RuleProposal(
        rule_version=f"{base_version}-greedy",
        description="Remove all matching constraints to maximise match count",
        changes=[
            "name_similarity_threshold=0.0",
            "amount_tolerance_abs=999999999.0",
            "date_tolerance_days=365",
            "min_confidence=0.0",
        ],
        rationale="Aggressive matching — optimise for match count regardless of accuracy.",
        proposed_by="demo",
    )

    job_id = uuid.uuid4().hex[:8]
    await crud.create_job(db, job_id, tenant.id)
    asyncio.create_task(_run_verify_job(job_id, tenant.id, greedy_proposal, rules))
    return {"job_id": job_id, "status": "running", "message": "Greedy attack started. Poll GET /jobs/{job_id}."}


@app.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    job = await crud.get_job(db, job_id, tenant.id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found.")
    return {"status": job.status, "result": job.result, "error": job.error, "progress": job.progress}


@app.get("/verify/latest")
async def get_latest_verify(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    row = await crud.get_latest_verify_report(db, tenant.id)
    if not row:
        raise HTTPException(404, "No verify report yet.")
    return row.report


# ── Approve / Reject / Rollback ────────────────────────────────────────────────

@app.post("/approve")
async def approve(
    req: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    verify_row = await crud.get_latest_verify_report(db, tenant.id)
    if not verify_row:
        raise HTTPException(400, "No verify report. POST /verify first.")

    report = _verify_from_dict(verify_row.report)
    if report.verdict != VerifyVerdict.GENUINE_IMPROVEMENT:
        raise HTTPException(400, f"Cannot approve: verdict is {report.verdict.value}")

    version = req.rule_version or report.rule_version
    rv = await crud.get_rule_version(db, tenant.id, version)
    if not rv:
        raise HTTPException(404, f"Rule version '{version}' not registered.")

    await crud.set_current_rule_version(db, tenant.id, version)

    proposal_row = await crud.get_latest_proposal(db, tenant.id)
    p = _proposal_from_dict(proposal_row.proposal) if proposal_row else None
    await _record_iteration(db, tenant.id, report, p, "approved")

    await crud.clear_proposal(db, tenant.id)
    await crud.clear_verify_report(db, tenant.id)

    current = await crud.get_current_rule_version(db, tenant.id)
    return {"approved": True, "active_version": current.version}


@app.post("/reject")
async def reject(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    verify_row = await crud.get_latest_verify_report(db, tenant.id)
    if not verify_row:
        raise HTTPException(400, "No verify report to reject.")
    report = _verify_from_dict(verify_row.report)
    proposal_row = await crud.get_latest_proposal(db, tenant.id)
    p = _proposal_from_dict(proposal_row.proposal) if proposal_row else None
    await _record_iteration(db, tenant.id, report, p, "rejected")
    await crud.clear_proposal(db, tenant.id)
    await crud.clear_verify_report(db, tenant.id)
    return {"rejected": True}


@app.post("/rollback/{version}")
async def rollback(
    version: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    rv = await crud.get_rule_version(db, tenant.id, version)
    if not rv:
        raise HTTPException(404, f"Version '{version}' not found.")
    await crud.set_current_rule_version(db, tenant.id, version)
    return {"rolled_back_to": version}


# ── History ────────────────────────────────────────────────────────────────────

@app.get("/history")
async def get_history(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    rows = await crud.get_iterations(db, tenant.id)
    return {"iterations": [r.data for r in rows]}


@app.post("/history/reset")
async def reset_history(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    await crud.clear_iterations(db, tenant.id)
    await crud.clear_proposal(db, tenant.id)
    await crud.clear_verify_report(db, tenant.id)
    versions = await crud.list_rule_versions(db, tenant.id)
    for v in versions:
        if v.version not in ("v0", "v1", "v_greedy"):
            from sqlalchemy import delete
            from backend.db.models import RuleVersion
            async with (await get_db().__anext__()) as s:
                await s.execute(delete(RuleVersion).where(RuleVersion.id == v.id))
                await s.commit()
    await crud.set_current_rule_version(db, tenant.id, "v0")
    return {"reset": True}


# ── Demo Seed ──────────────────────────────────────────────────────────────────

@app.post("/demo/seed")
async def demo_seed(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    """Instantly seed full 3-layer demo state — no Gemini calls."""
    await _ensure_default_rules(db, tenant.id)

    reconcile_results = [
        {"payment_id": "PAY001", "decision": "matched", "matched_invoice_id": "INV001", "confidence": 1.0, "rationale": "Exact name and amount match."},
        {"payment_id": "PAY002", "decision": "matched", "matched_invoice_id": "INV002", "confidence": 1.0, "rationale": "Exact match on all fields."},
        {"payment_id": "PAY003", "decision": "matched", "matched_invoice_id": "INV003", "confidence": 1.0, "rationale": "Exact name and amount match."},
        {"payment_id": "PAY004", "decision": "matched", "matched_invoice_id": "INV004", "confidence": 1.0, "rationale": "Exact match."},
        {"payment_id": "PAY005", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
        {"payment_id": "PAY006", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
        {"payment_id": "PAY007", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
        {"payment_id": "PAY008", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
        {"payment_id": "PAY009", "decision": "matched", "matched_invoice_id": "INV009", "confidence": 1.0, "rationale": "Name exact match. Small fee deduction within tolerance."},
        {"payment_id": "PAY010", "decision": "matched", "matched_invoice_id": "INV010", "confidence": 0.98, "rationale": "Name match. Amount differs by Rp 6,500 (bank fee deduction)."},
        {"payment_id": "PAY011", "decision": "matched", "matched_invoice_id": "INV011", "confidence": 1.0, "rationale": "Name and amount exact. Date 2 days apart within tolerance."},
        {"payment_id": "PAY012", "decision": "matched", "matched_invoice_id": "INV012", "confidence": 0.98, "rationale": "Exact match on name and amount."},
        {"payment_id": "PAY013", "decision": "matched", "matched_invoice_id": "INV013A+INV013B", "confidence": 0.98, "rationale": "Split payment: INV013A (5M) + INV013B (3.5M) = 8.5M total."},
        {"payment_id": "PAY014", "decision": "matched", "matched_invoice_id": "INV014A+INV014B", "confidence": 0.98, "rationale": "Split payment: INV014A + INV014B matches total."},
        {"payment_id": "PAY015", "decision": "matched", "matched_invoice_id": "INV015", "confidence": 1.0, "rationale": "Exact match on all fields."},
        {"payment_id": "PAY016", "decision": "matched", "matched_invoice_id": "INV016", "confidence": 0.98, "rationale": "Name and amount match. Correct vendor despite duplicate amount."},
        {"payment_id": "PAY017", "decision": "matched", "matched_invoice_id": "INV017", "confidence": 1.0, "rationale": "Exact match on all fields."},
        {"payment_id": "PAY018", "decision": "matched", "matched_invoice_id": "INV018", "confidence": 1.0, "rationale": "Exact match on all fields."},
        {"payment_id": "PAY019", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
        {"payment_id": "PAY020", "decision": "unmatched", "matched_invoice_id": None, "confidence": 0.95, "rationale": "No candidates passed name similarity filter (threshold=0.95). Auto-unmatched."},
    ]

    await crud.save_reconcile_result(db, tenant.id, {
        "results": reconcile_results, "accuracy": 0.80, "total": 20, "correct": 16, "rule_version": "v0",
    })

    proposal_dict = {
        "rule_version": "v1-proposed",
        "description": "Relax name similarity and tolerances to handle vendor name variants and bank fee deductions",
        "changes": ["name_similarity_threshold=0.7", "amount_tolerance_abs=10000.0", "date_tolerance_days=5", "min_confidence=0.6"],
        "rationale": "4 payments (PAY005–PAY008) were auto-rejected because their payer names fell below the 0.95 similarity threshold.",
        "proposed_by": "judge",
    }
    await crud.save_proposal(db, tenant.id, proposal_dict)

    proposal = _proposal_from_dict(proposal_dict)
    v1_rules = apply_rule_proposal(proposal, base_version="v0")
    await crud.upsert_rule_version(db, tenant.id, "v1-proposed", _rules_to_dict(v1_rules))

    verify_dict = {
        "rule_version": "v1-proposed",
        "score_train": 1.0, "score_holdout": 1.0,
        "score_baseline_train": 0.80, "score_baseline_holdout": 0.90,
        "delta_train": 0.20, "delta_holdout": 0.10,
        "verdict": "GENUINE_IMPROVEMENT",
        "explanation": "Holdout accuracy improved by +10.0% (90.0% → 100.0%). Rule changes generalise to unseen data. Recommend human approval.",
    }
    await crud.save_verify_report(db, tenant.id, verify_dict)

    await crud.clear_iterations(db, tenant.id)
    vr = _verify_from_dict(verify_dict)
    await _record_iteration(db, tenant.id, vr, proposal, "approved")

    hacking_vr = VerifyReport(
        rule_version="v1-greedy", score_train=0.90, score_holdout=0.90,
        score_baseline_train=1.0, score_baseline_holdout=1.0,
        delta_train=-0.10, delta_holdout=-0.10,
        verdict=VerifyVerdict.REWARD_HACKING,
        explanation="REWARD HACKING DETECTED: Rules degraded both splits — train -10.0%, holdout -10.0%.",
    )
    greedy_p = RuleProposal(rule_version="v1-greedy", description="Greedy attack: remove all constraints", changes=[], rationale="")
    await _record_iteration(db, tenant.id, hacking_vr, greedy_p, "rejected")

    return {
        "seeded": True,
        "reconcile": "16/20 = 80% (v0 baseline)",
        "proposal": "v1-style rule relaxation",
        "verify": "GENUINE_IMPROVEMENT (+10% holdout)",
        "history": "2 iterations pre-loaded",
    }


@app.post("/demo/seed-hacking")
async def demo_seed_hacking(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    verify_dict = {
        "rule_version": "v1-greedy",
        "score_train": 0.90, "score_holdout": 0.90,
        "score_baseline_train": 1.0, "score_baseline_holdout": 1.0,
        "delta_train": -0.10, "delta_holdout": -0.10,
        "verdict": "REWARD_HACKING",
        "explanation": "REWARD HACKING DETECTED: Rules degraded both splits — train -10.0%, holdout -10.0% (100.0% → 90.0%). Proposal auto-rejected.",
    }
    await crud.save_verify_report(db, tenant.id, verify_dict)

    proposal_dict = {
        "rule_version": "v1-greedy",
        "description": "Remove all matching constraints to maximise match count",
        "changes": ["name_similarity_threshold=0.0", "amount_tolerance_abs=999999999.0", "date_tolerance_days=365", "min_confidence=0.0"],
        "rationale": "Aggressive matching.",
        "proposed_by": "demo",
    }
    await crud.save_proposal(db, tenant.id, proposal_dict)
    return {"seeded": True, "verdict": "REWARD_HACKING"}


# ── Production root app (frontend + API at /api) ───────────────────────────────

import os as _os

_root = FastAPI(title="HonestLedger")
_root.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@_root.on_event("startup")
async def _root_startup():
    """Lifecycle events on mounted sub-apps don't fire — must attach to root app."""
    await init_db()
    try:
        setup_phoenix_tracing()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Phoenix tracing skipped: {e}")


_root.mount("/api", app)

_frontend_dist = _os.path.join(_os.path.dirname(__file__), "..", "frontend", "dist")
if _os.path.exists(_frontend_dist):
    _root.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
