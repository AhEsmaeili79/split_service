from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    slug: str
    created_by: str
    created_at: datetime


class GroupMemberBase(BaseModel):
    user_id: Optional[str] = None
    is_admin: bool = False


class GroupMemberCreate(GroupMemberBase):
    # Support both user_id and phone/email lookup
    phone: Optional[str] = None
    email: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate that either user_id or phone/email is provided
        if not self.user_id and not self.phone and not self.email:
            raise ValueError("Either user_id, phone, or email must be provided")
        if self.user_id and (self.phone or self.email):
            raise ValueError("Cannot provide both user_id and phone/email")
        if self.phone and self.email:
            raise ValueError("Cannot provide both phone and email")


class SimpleGroupMemberCreate(BaseModel):
    """Simple schema for adding group members with just identifier and admin status"""
    is_admin: bool = False
    identifier: str  # Can be email or phone number


class GroupMemberOut(GroupMemberBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    group_id: str
    joined_at: datetime


class AsyncMemberRequestOut(BaseModel):
    """Response schema for async member addition requests"""
    message: str
    request_id: str
    status: str
    phone_or_email: str


class PendingRequestStatusOut(BaseModel):
    """Response schema for pending request status"""
    model_config = ConfigDict(from_attributes=True)
    
    request_id: str
    phone_or_email: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GroupWithMembers(GroupOut):
    model_config = ConfigDict(from_attributes=True)
    
    members: List[GroupMemberOut] = []


class GroupCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)


class GroupCategoryCreate(GroupCategoryBase):
    pass


class GroupCategoryOut(GroupCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    group_id: str
    created_at: datetime


class GroupCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
