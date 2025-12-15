from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.lab.models import LabTestCatalog, LabOrder, LabResult


class LabRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(self, order_data: dict) -> LabOrder:
        order = LabOrder(**order_data)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_order(self, order_id: str) -> Optional[LabOrder]:
        result = await self.db.execute(select(LabOrder).where(LabOrder.id == order_id))
        return result.scalar_one_or_none()

    async def add_result(self, result_data: dict) -> LabResult:
        result = LabResult(**result_data)
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result
