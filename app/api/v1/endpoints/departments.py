from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.department import Department
from app.models.user import User, UserRole
from app.schemas import department as department_schema

router = APIRouter()

@router.get("/", response_model=List[department_schema.Department])
async def read_departments(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    result = await db.execute(select(Department).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=department_schema.Department)
async def create_department(
    *,
    db: AsyncSession = Depends(get_db),
    dept_in: department_schema.DepartmentCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    dept = Department(**dept_in.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept
