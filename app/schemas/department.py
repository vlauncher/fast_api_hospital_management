from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    head_doctor_id: Optional[UUID] = None
    floor_number: Optional[int] = None
    contact_extension: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(DepartmentBase):
    name: Optional[str] = None

class Department(DepartmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
