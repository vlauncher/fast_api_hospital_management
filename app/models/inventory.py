from sqlalchemy import Column, String, ForeignKey, Date, Text, JSON, Enum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
import uuid
from datetime import datetime

class InventoryType(str, enum.Enum):
    MEDICINE = "medicine"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    item_name = Column(String(255), nullable=False)
    item_type = Column(Enum(InventoryType), nullable=False)
    quantity = Column(Integer, default=0)
    unit = Column(String(50))
    expiry_date = Column(Date)
    supplier = Column(String(255))
    reorder_level = Column(Integer, default=10)
    ai_demand_forecast = Column(JSON, default={})
    
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)
