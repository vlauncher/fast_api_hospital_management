from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid

# Base Mixin for Tenant Isolation
class TenantMixin:
    tenant_id = Column(String(50), nullable=True, index=True) # Could be UUID, string for simplicity now
