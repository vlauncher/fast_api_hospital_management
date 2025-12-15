from pydantic import BaseModel
from typing import Optional


class LabOrderCreate(BaseModel):
    patient_id: str
    ordered_by: Optional[str]
    tests: list


class LabOrderResponse(BaseModel):
    id: str
    patient_id: str
    ordered_by: Optional[str]
    status: str

    class Config:
        orm_mode = True


class LabResultCreate(BaseModel):
    order_id: str
    result: str


class LabResultResponse(BaseModel):
    id: str
    order_id: str
    result: str
    verified: bool

    class Config:
        orm_mode = True
