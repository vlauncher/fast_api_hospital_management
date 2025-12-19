from sqlalchemy import Column, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
import uuid
from datetime import datetime

class BedType(str, enum.Enum):
    GENERAL = "general"
    ICU = "icu"
    PRIVATE = "private"
    SEMI_PRIVATE = "semi_private"

class BedStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"

class Bed(Base):
    __tablename__ = "hospital_beds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    bed_number = Column(String(20), unique=True, nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    bed_type = Column(Enum(BedType), default=BedType.GENERAL)
    status = Column(Enum(BedStatus), default=BedStatus.AVAILABLE)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    assigned_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", backref="beds")
    patient = relationship("Patient", backref="assigned_bed")
