from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.domain.lab.service import LabService
from app.api.v1.lab.schemas import (
    LabOrderCreate, LabOrderResponse, LabResultCreate, LabResultResponse
)

router = APIRouter(tags=["Lab"])


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_in: LabOrderCreate, db: AsyncSession = Depends(get_db)):
    service = LabService(db)
    order = await service.create_order(order_in.dict())
    return LabOrderResponse.from_orm(order)


@router.post("/results", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def add_result(result_in: LabResultCreate, db: AsyncSession = Depends(get_db)):
    service = LabService(db)
    res = await service.add_result(result_in.dict())
    return LabResultResponse.from_orm(res)
