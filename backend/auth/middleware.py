"""API key authentication — resolves X-API-Key header to tenant_id."""

from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db
from backend.db.crud import resolve_api_key
from backend.db.models import Tenant


async def get_tenant(
    x_api_key: str = Header(..., description="API key in format hl_<32hex>"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """FastAPI dependency: validates X-API-Key and returns the Tenant."""
    tenant = await resolve_api_key(db, x_api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return tenant
