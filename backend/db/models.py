"""SQLAlchemy ORM models — one table per domain concept, all scoped to tenant_id."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Float, Integer, Text, DateTime, ForeignKey, JSON, text
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
    consecutive_verify_failures: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="tenant", cascade="all, delete")
    jobs: Mapped[list["Job"]] = relationship(back_populates="tenant", cascade="all, delete")
    reconcile_results: Mapped[list["ReconcileResult"]] = relationship(back_populates="tenant", cascade="all, delete")
    rule_proposals: Mapped[list["RuleProposal"]] = relationship(back_populates="tenant", cascade="all, delete")
    verify_reports: Mapped[list["VerifyReport"]] = relationship(back_populates="tenant", cascade="all, delete")
    iterations: Mapped[list["IterationRecord"]] = relationship(back_populates="tenant", cascade="all, delete")
    uploads: Mapped[list["TenantUpload"]] = relationship(back_populates="tenant", cascade="all, delete")
    rule_versions: Mapped[list["RuleVersion"]] = relationship(back_populates="tenant", cascade="all, delete")
    schema_mappings: Mapped[list["TenantSchemaMapping"]] = relationship(back_populates="tenant", cascade="all, delete")


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


class TenantSchemaMapping(Base):
    """Stores column mapping configuration per tenant per file type. Versioned for drift detection."""
    __tablename__ = "tenant_schema_mappings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    file_type: Mapped[str] = mapped_column(String, nullable=False)   # "payments" | "invoices"
    column_map: Mapped[dict] = mapped_column(JSON, nullable=False)    # {"Date": "date", ...}
    schema_fingerprint: Mapped[str] = mapped_column(String, nullable=False)  # hash of sorted column names
    mapping_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="schema_mappings")


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


class OAuthUser(Base):
    """Google OAuth users — each maps 1-to-1 with a Tenant."""
    __tablename__ = "oauth_users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    google_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    picture: Mapped[str] = mapped_column(String, nullable=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PendingReveal(Base):
    """Short-lived record that holds a raw API key for one-time display after OAuth login."""
    __tablename__ = "pending_reveals"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)  # SHA256 of raw token
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    api_key_raw: Mapped[str] = mapped_column(String, nullable=False)
    user_email: Mapped[str] = mapped_column(String, nullable=True)
    user_name: Mapped[str] = mapped_column(String, nullable=True)
    user_picture: Mapped[str] = mapped_column(String, nullable=True)
    is_new_user: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
