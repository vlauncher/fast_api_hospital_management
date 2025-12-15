from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.pharmacy.models import Drug, PharmacyDispensing, DispensingItem
import uuid


class PharmacyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_drug(self, data: dict) -> Drug:
        drug = Drug(**data)
        self.db.add(drug)
        await self.db.commit()
        await self.db.refresh(drug)
        return drug

    async def get_drug(self, drug_id: str) -> Optional[Drug]:
        result = await self.db.execute(select(Drug).where(Drug.id == drug_id))
        return result.scalar_one_or_none()

    async def list_drugs(self, limit: int = 100) -> List[Drug]:
        result = await self.db.execute(select(Drug).limit(limit))
        return result.scalars().all()

    async def create_dispensing(self, dispensing_data: dict, items: List[dict]) -> PharmacyDispensing:
        dispensing = PharmacyDispensing(**dispensing_data)
        self.db.add(dispensing)
        await self.db.flush()

        for it in items:
            di = DispensingItem(dispensing_id=dispensing.id, **it)
            self.db.add(di)

        await self.db.commit()
        await self.db.refresh(dispensing)
        return dispensing
