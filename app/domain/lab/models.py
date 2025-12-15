from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
import uuid

from app.infrastructure.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class LabTestCatalog(Base):
    __tablename__ = "lab_test_catalog"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    patient_id = Column(String(36), nullable=False)
    ordered_by = Column(String(36), nullable=True)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=func.now())


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    order_id = Column(String(36), ForeignKey("lab_orders.id"), nullable=False)
    result = Column(Text, nullable=False)
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)

    order = relationship("LabOrder", backref="results")
