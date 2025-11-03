from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ExpenseBase(BaseModel):
    group_category_id: str
    title: str = Field(..., max_length=200)
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    date: datetime


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    date: Optional[datetime] = None


class ExpenseOut(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    group_id: str
    paid_by: str
    created_at: datetime


class ExpenseShareBase(BaseModel):
    user_id: str
    share_amount: Decimal = Field(..., ge=0)


class ExpenseShareCreate(ExpenseShareBase):
    pass


class ExpenseShareOut(ExpenseShareBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    expense_id: str
    is_settled: bool


class ExpenseWithShares(ExpenseOut):
    shares: List[ExpenseShareOut] = []


class DebtSummary(BaseModel):
    user_id: str
    total_owed: Decimal
    total_owes: Decimal
    net_balance: Decimal
