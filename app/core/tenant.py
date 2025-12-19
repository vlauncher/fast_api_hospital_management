from contextvars import ContextVar
from typing import Optional

tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_context", default=None)

def get_tenant_id() -> Optional[str]:
    return tenant_context.get()

def set_tenant_id(tenant_id: str):
    tenant_context.set(tenant_id)
