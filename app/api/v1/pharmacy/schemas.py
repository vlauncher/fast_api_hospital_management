from pydantic import BaseModel, Field
from typing import List, Optional


class DrugCreate(BaseModel):
    name: str
    code: Optional[str]
    description: Optional[str]
    unit_price: Optional[int]


class DrugResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    description: Optional[str]
    unit_price: Optional[int]

    class Config:
        orm_mode = True


class DispenseItem(BaseModel):
    drug_id: str
    quantity: int = Field(..., gt=0)
    instructions: Optional[str]


class DispenseRequest(BaseModel):
    prescription_id: Optional[str]
    patient_id: str
    dispensed_by: Optional[str]
    notes: Optional[str]
    items: List[DispenseItem]


class DispenseResponse(BaseModel):
    id: str
    prescription_id: Optional[str]
    patient_id: str
    dispensed_by: Optional[str]
    dispensed_at: Optional[str]

    class Config:
        orm_mode = True
