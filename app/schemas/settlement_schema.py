from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    group_id: str
    settled_at: datetime


class OptimizedSettlement(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Decimal
