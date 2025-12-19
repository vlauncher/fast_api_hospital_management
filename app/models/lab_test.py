from sqlalchemy import Column, String, ForeignKey, Date, JSON, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum
import uuid
from datetime import datetime

class LabTestStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class LabTest(Base):
    __tablename__ = "lab_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    
    test_name = Column(String(255), nullable=False)
    test_type = Column(String(100))
    test_date = Column(Date)
    results = Column(JSON, default={})
    ai_interpretation = Column(Text)
    status = Column(Enum(LabTestStatus), default=LabTestStatus.PENDING)
    file_url = Column(String(500)) # Link to results document in Cloudinary
    
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", backref="lab_tests")
    doctor = relationship("Doctor", backref="lab_tests")
