from sqlalchemy import Column, String, ForeignKey, Integer, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid
from datetime import datetime

class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    head_doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True)
    floor_number = Column(Integer)
    contact_extension = Column(String(20))
    
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)

    head_doctor = relationship("Doctor", foreign_keys=[head_doctor_id])
