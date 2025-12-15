from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.pharmacy.repository import PharmacyRepository


class PharmacyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PharmacyRepository(db)

    async def create_drug(self, drug_in: dict):
        return await self.repo.create_drug(drug_in)

    async def list_drugs(self, limit: int = 100):
        return await self.repo.list_drugs(limit=limit)

    async def dispense(self, dispensing_data: dict, items: List[dict]):
        # Basic business rule: ensure items exist and quantity > 0
        for it in items:
            if it.get("quantity", 0) <= 0:
                raise ValueError("Quantity must be greater than zero")

        dispensing = await self.repo.create_dispensing(dispensing_data, items)
        return dispensing
