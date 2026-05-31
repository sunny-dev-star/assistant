"""Push device repository"""
from sqlalchemy import select
from ..models.bff_models import PushDeviceModel


class PushDeviceRepository:
    def __init__(self, session):
        self.session = session

    async def upsert(self, data: dict):
        stmt = select(PushDeviceModel).where(
            PushDeviceModel.user_id == data["user_id"],
            PushDeviceModel.device_token == data["device_token"],
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.platform = data["platform"]
            existing.is_active = True
        else:
            device = PushDeviceModel(**data)
            self.session.add(device)
        await self.session.flush()

    async def get_active_devices(self, user_id: str, tenant_id: str) -> list[dict]:
        stmt = select(PushDeviceModel).where(
            PushDeviceModel.user_id == user_id,
            PushDeviceModel.tenant_id == tenant_id,
            PushDeviceModel.is_active == True,
        )
        results = (await self.session.execute(stmt)).scalars().all()
        return [
            {"platform": d.platform, "device_token": d.device_token}
            for d in results
        ]
