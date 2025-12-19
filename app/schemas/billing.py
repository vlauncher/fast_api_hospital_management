from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.models.billing import PaymentStatus

class BillingBase(BaseModel):
    patient_id: UUID
    appointment_id: Optional[UUID] = None
    total_amount: float
    paid_amount: Optional[float] = 0.0
    pending_amount: float
    payment_status: Optional[PaymentStatus] = PaymentStatus.PENDING
    payment_method: Optional[str] = None
    bill_items: Optional[List[dict]] = []

class BillingCreate(BillingBase):
    pass

class BillingUpdate(BaseModel):
    paid_amount: Optional[float] = None
    pending_amount: Optional[float] = None
    payment_status: Optional[PaymentStatus] = None
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None

class Billing(BillingBase):
    id: UUID
    generated_date: datetime
    payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
