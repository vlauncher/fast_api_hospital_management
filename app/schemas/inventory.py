from typing import Optional
from pydantic import BaseModel
from datetime import date
from uuid import UUID
from app.models.inventory import InventoryType

class InventoryBase(BaseModel):
    item_name: str
    item_type: InventoryType
    quantity: Optional[int] = 0
    unit: Optional[str] = None
    expiry_date: Optional[date] = None
    supplier: Optional[str] = None
    reorder_level: Optional[int] = 10

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(InventoryBase):
    item_name: Optional[str] = None
    item_type: Optional[InventoryType] = None

class InventoryInDBBase(InventoryBase):
    id: UUID
    ai_demand_forecast: Optional[dict] = {}
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True

class Inventory(InventoryInDBBase):
    pass
