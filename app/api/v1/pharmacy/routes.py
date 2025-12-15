from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.infrastructure.database import get_db
from app.domain.pharmacy.service import PharmacyService
from app.api.v1.pharmacy.schemas import (
    DrugCreate, DrugResponse, DispenseRequest, DispenseResponse
)

router = APIRouter(tags=["Pharmacy"])


@router.post("/drugs", response_model=DrugResponse, status_code=status.HTTP_201_CREATED)
async def create_drug(drug_in: DrugCreate, db: AsyncSession = Depends(get_db)):
    service = PharmacyService(db)
    drug = await service.create_drug(drug_in.dict())
    return DrugResponse.from_orm(drug)


@router.get("/drugs", response_model=List[DrugResponse])
async def list_drugs(db: AsyncSession = Depends(get_db)):
    service = PharmacyService(db)
    drugs = await service.list_drugs()
    return [DrugResponse.from_orm(d) for d in drugs]


@router.post("/dispense", response_model=DispenseResponse, status_code=status.HTTP_201_CREATED)
async def dispense(request: DispenseRequest, db: AsyncSession = Depends(get_db)):
    service = PharmacyService(db)
    try:
        dispensing = await service.dispense(
            {k: v for k, v in request.dict().items() if k != "items"},
            [i.dict() for i in request.items]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DispenseResponse.from_orm(dispensing)
