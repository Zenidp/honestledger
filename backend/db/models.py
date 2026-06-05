"""SQLAlchemy ORM models — one table per domain concept, all scoped to tenant_id."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Float, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="tenant", cascade="all, delete")
    jobs: Mapped[list["Job"]] = relationship(back_populates="tenant", cascade="all, delete")
    reconcile_results: Mapped[list["ReconcileResult"]] = relationship(back_populates="tenant", cascade="all, delete")
    rule_proposals: Mapped[list["RuleProposal"]] = relationship(back_populates="tenant", cascade="all, delete")
    verify_reports: Mapped[list["VerifyReport"]] = relationship(back_populates="tenant", cascade="all, delete")
    iterations: Mapped[list["IterationRecord"]] = relationship(back_populates="tenant", cascade="all, delete")
    uploads: Mapped[list["TenantUpload"]] = relationship(back_populates="tenant", cascade="all, delete")
    rule_versions: Mapped[list["RuleVersion"]] = relationship(back_populates="tenant", cascade="all, delete")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)  # first 8 chars for display
    name: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="api_keys")


class TenantUpload(Base):
    """Stores parsed CSV data uploaded by tenant."""
    __tablename__ = "tenant_uploads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    payments: Mapped[dict] = mapped_column(JSON, default=list)
    invoices: Mapped[dict] = mapped_column(JSON, default=list)
    ground_truth: Mapped[dict] = mapped_column(JSON, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="uploads")


class RuleVersion(Base):
    """Rule set versions per tenant."""
    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="rule_versions")


class ReconcileResult(Base):
    __tablename__ = "reconcile_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    total: Mapped[int] = mapped_column(Integer, nullable=True)
    correct: Mapped[int] = mapped_column(Integer, nullable=True)
    rule_version: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="reconcile_results")


class RuleProposal(Base):
    __tablename__ = "rule_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    proposal: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="rule_proposals")


class VerifyReport(Base):
    __tablename__ = "verify_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="verify_reports")


class IterationRecord(Base):
    __tablename__ = "iteration_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    iteration_num: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="iterations")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | running | done | error
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    progress: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="jobs")
