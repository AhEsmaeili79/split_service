from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class SettlementBase(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Decimal = Field(..., gt=0)


class SettlementCreate(SettlementBase):
    pass


class SettlementOut(SettlementBase):
    id: str
    group_id: str
    settled_at: datetime

    class Config:
        from_attributes = True


class OptimizedSettlement(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Decimal
