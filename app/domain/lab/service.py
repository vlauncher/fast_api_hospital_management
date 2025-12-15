from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.lab.repository import LabRepository


class LabService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LabRepository(db)

    async def create_order(self, order_in: dict):
        return await self.repo.create_order(order_in)

    async def add_result(self, result_in: dict):
        # Basic verification and creation
        return await self.repo.add_result(result_in)
