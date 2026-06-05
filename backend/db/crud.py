"""Async CRUD operations — all queries scoped by tenant_id."""

import hashlib
import secrets
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import (
    Tenant, ApiKey, TenantUpload, RuleVersion,
    ReconcileResult, RuleProposal, VerifyReport, IterationRecord, Job,
)


# ── API Key helpers ────────────────────────────────────────────────────────────

def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key in format hl_<32 random hex chars>."""
    return "hl_" + secrets.token_hex(16)


# ── Tenant ────────────────────────────────────────────────────────────────────

async def create_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def get_tenant_by_id(db: AsyncSession, tenant_id: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


# ── API Keys ──────────────────────────────────────────────────────────────────

async def create_api_key(db: AsyncSession, tenant_id: str, name: str = None) -> tuple[str, ApiKey]:
    """Create a new API key. Returns (raw_key, ApiKey row). Raw key shown only once."""
    raw_key = generate_api_key()
    key_row = ApiKey(
        tenant_id=tenant_id,
        key_hash=_hash_key(raw_key),
        key_prefix=raw_key[:8],
        name=name,
    )
    db.add(key_row)
    await db.commit()
    await db.refresh(key_row)
    return raw_key, key_row


async def resolve_api_key(db: AsyncSession, raw_key: str) -> Tenant | None:
    """Validate API key and return its Tenant, or None if invalid/inactive."""
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    key_row = result.scalar_one_or_none()
    if not key_row:
        return None
    return await get_tenant_by_id(db, key_row.tenant_id)


async def list_api_keys(db: AsyncSession, tenant_id: str) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).where(ApiKey.tenant_id == tenant_id))
    return list(result.scalars().all())


# ── Uploads ───────────────────────────────────────────────────────────────────

async def save_upload(db: AsyncSession, tenant_id: str, payments: list, invoices: list, ground_truth: dict) -> TenantUpload:
    upload = TenantUpload(tenant_id=tenant_id, payments=payments, invoices=invoices, ground_truth=ground_truth)
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return upload


async def get_latest_upload(db: AsyncSession, tenant_id: str) -> TenantUpload | None:
    result = await db.execute(
        select(TenantUpload)
        .where(TenantUpload.tenant_id == tenant_id)
        .order_by(TenantUpload.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Rule Versions ─────────────────────────────────────────────────────────────

async def upsert_rule_version(db: AsyncSession, tenant_id: str, version: str, config: dict) -> RuleVersion:
    result = await db.execute(
        select(RuleVersion).where(RuleVersion.tenant_id == tenant_id, RuleVersion.version == version)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.config = config
        await db.commit()
        return existing
    rv = RuleVersion(tenant_id=tenant_id, version=version, config=config)
    db.add(rv)
    await db.commit()
    await db.refresh(rv)
    return rv


async def set_current_rule_version(db: AsyncSession, tenant_id: str, version: str):
    await db.execute(update(RuleVersion).where(RuleVersion.tenant_id == tenant_id).values(is_current=False))
    await db.execute(
        update(RuleVersion)
        .where(RuleVersion.tenant_id == tenant_id, RuleVersion.version == version)
        .values(is_current=True)
    )
    await db.commit()


async def get_current_rule_version(db: AsyncSession, tenant_id: str) -> RuleVersion | None:
    result = await db.execute(
        select(RuleVersion).where(RuleVersion.tenant_id == tenant_id, RuleVersion.is_current == True)
    )
    return result.scalar_one_or_none()


async def get_rule_version(db: AsyncSession, tenant_id: str, version: str) -> RuleVersion | None:
    result = await db.execute(
        select(RuleVersion).where(RuleVersion.tenant_id == tenant_id, RuleVersion.version == version)
    )
    return result.scalar_one_or_none()


async def list_rule_versions(db: AsyncSession, tenant_id: str) -> list[RuleVersion]:
    result = await db.execute(select(RuleVersion).where(RuleVersion.tenant_id == tenant_id))
    return list(result.scalars().all())


# ── Reconcile Results ─────────────────────────────────────────────────────────

async def save_reconcile_result(db: AsyncSession, tenant_id: str, data: dict) -> ReconcileResult:
    row = ReconcileResult(tenant_id=tenant_id, **data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_latest_reconcile(db: AsyncSession, tenant_id: str) -> ReconcileResult | None:
    result = await db.execute(
        select(ReconcileResult)
        .where(ReconcileResult.tenant_id == tenant_id)
        .order_by(ReconcileResult.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_reconcile_holdout(db: AsyncSession, row_id: str, holdout_accuracy: float) -> None:
    """Store holdout baseline score inside the results JSON of a reconcile row."""
    result = await db.execute(select(ReconcileResult).where(ReconcileResult.id == row_id))
    row = result.scalar_one_or_none()
    if row:
        row.results = {**row.results, "holdout_accuracy": holdout_accuracy}
        await db.commit()


# ── Rule Proposals ────────────────────────────────────────────────────────────

async def save_proposal(db: AsyncSession, tenant_id: str, proposal: dict) -> RuleProposal:
    row = RuleProposal(tenant_id=tenant_id, proposal=proposal)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_latest_proposal(db: AsyncSession, tenant_id: str) -> RuleProposal | None:
    result = await db.execute(
        select(RuleProposal)
        .where(RuleProposal.tenant_id == tenant_id)
        .order_by(RuleProposal.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def clear_proposal(db: AsyncSession, tenant_id: str):
    await db.execute(delete(RuleProposal).where(RuleProposal.tenant_id == tenant_id))
    await db.commit()


# ── Verify Reports ────────────────────────────────────────────────────────────

async def save_verify_report(db: AsyncSession, tenant_id: str, report: dict) -> VerifyReport:
    row = VerifyReport(tenant_id=tenant_id, report=report)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_latest_verify_report(db: AsyncSession, tenant_id: str) -> VerifyReport | None:
    result = await db.execute(
        select(VerifyReport)
        .where(VerifyReport.tenant_id == tenant_id)
        .order_by(VerifyReport.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def clear_verify_report(db: AsyncSession, tenant_id: str):
    await db.execute(delete(VerifyReport).where(VerifyReport.tenant_id == tenant_id))
    await db.commit()


# ── Iteration History ─────────────────────────────────────────────────────────

async def append_iteration(db: AsyncSession, tenant_id: str, data: dict) -> IterationRecord:
    count_result = await db.execute(
        select(func.count()).where(IterationRecord.tenant_id == tenant_id)
    )
    num = (count_result.scalar() or 0) + 1
    row = IterationRecord(tenant_id=tenant_id, iteration_num=num, data=data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_iterations(db: AsyncSession, tenant_id: str) -> list[IterationRecord]:
    result = await db.execute(
        select(IterationRecord)
        .where(IterationRecord.tenant_id == tenant_id)
        .order_by(IterationRecord.iteration_num)
    )
    return list(result.scalars().all())


async def clear_iterations(db: AsyncSession, tenant_id: str):
    await db.execute(delete(IterationRecord).where(IterationRecord.tenant_id == tenant_id))
    await db.commit()


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def create_job(db: AsyncSession, job_id: str, tenant_id: str) -> Job:
    row = Job(id=job_id, tenant_id=tenant_id, status="pending")
    db.add(row)
    await db.commit()
    return row


async def update_job(db: AsyncSession, job_id: str, tenant_id: str, **kwargs):
    from datetime import datetime, timezone
    kwargs["updated_at"] = datetime.now(timezone.utc)
    await db.execute(
        update(Job).where(Job.id == job_id, Job.tenant_id == tenant_id).values(**kwargs)
    )
    await db.commit()


async def get_job(db: AsyncSession, job_id: str, tenant_id: str) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()
