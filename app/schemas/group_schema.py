from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RoundingOption(str, Enum):
    up = "up"
    down = "down"
    none = "none"


class GroupBase(BaseModel):
    name: str = Field(..., max_length=100)
    image_url: Optional[str] = None
    rounding_option: RoundingOption = RoundingOption.none


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    rounding_option: Optional[RoundingOption] = None
    # Note: slug is auto-generated and cannot be manually updated


class GroupOut(GroupBase):
    id: str
    slug: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class GroupMemberBase(BaseModel):
    user_id: str
    is_admin: bool = False


class GroupMemberCreate(GroupMemberBase):
    pass


class GroupMemberOut(GroupMemberBase):
    id: str
    group_id: str
    joined_at: datetime

    class Config:
        from_attributes = True


class GroupWithMembers(GroupOut):
    members: List[GroupMemberOut] = []

    class Config:
        from_attributes = True


class GroupCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)


class GroupCategoryCreate(GroupCategoryBase):
    pass


class GroupCategoryOut(GroupCategoryBase):
    id: str
    group_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class GroupCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
