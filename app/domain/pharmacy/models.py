from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    unit_price = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())


class PharmacyDispensing(Base):
    __tablename__ = "pharmacy_dispensing"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    prescription_id = Column(String(36), nullable=True)
    patient_id = Column(String(36), nullable=False)
    dispensed_by = Column(String(36), nullable=True)
    dispensed_at = Column(DateTime, default=func.now())
    notes = Column(Text, nullable=True)


class DispensingItem(Base):
    __tablename__ = "dispensing_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    dispensing_id = Column(String(36), ForeignKey("pharmacy_dispensing.id"), nullable=False)
    drug_id = Column(String(36), ForeignKey("drugs.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    instructions = Column(Text, nullable=True)

    dispensing = relationship("PharmacyDispensing", backref="items")
