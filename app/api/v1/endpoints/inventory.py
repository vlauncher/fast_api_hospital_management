from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.session import get_db
from app.models.inventory import Inventory
from app.models.user import User, UserRole
from app.schemas import inventory as inventory_schema

router = APIRouter()

@router.get("/", response_model=List[inventory_schema.Inventory])
async def read_inventory(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve inventory items.
    """
    result = await db.execute(select(Inventory).offset(skip).limit(limit))
    items = result.scalars().all()
    return items

@router.post("/", response_model=inventory_schema.Inventory)
async def create_inventory_item(
    *,
    db: AsyncSession = Depends(get_db),
    item_in: inventory_schema.InventoryCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new inventory item (Admin/Staff only).
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.RECEPTIONIST]: # Simplified permissions
         raise HTTPException(status_code=403, detail="Not enough permissions")
    
    item = Inventory(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/{item_id}", response_model=inventory_schema.Inventory)
async def update_inventory_item(
    item_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    item_in: inventory_schema.InventoryUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update inventory item.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.RECEPTIONIST]:
         raise HTTPException(status_code=403, detail="Not enough permissions")
         
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
