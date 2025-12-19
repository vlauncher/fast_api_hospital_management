from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.tenant import set_tenant_id

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            set_tenant_id(tenant_id)
        
        response = await call_next(request)
        return response
