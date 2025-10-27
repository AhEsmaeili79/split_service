from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Union
from app.db.database import get_db
from app.services.auth.jwt_handler import get_current_user
from app.services.group_service import (
    create_group, get_group, get_group_by_slug, get_user_groups, update_group, delete_group,
    add_member_to_group, add_member_to_group_enhanced, remove_member_from_group, get_group_members,
    create_group_category, get_group_categories, update_group_category, delete_group_category
)
from app.schemas.group_schema import (
    GroupCreate, GroupUpdate, GroupOut, GroupMemberCreate, GroupMemberOut,
    GroupWithMembers, GroupCategoryCreate, GroupCategoryOut, GroupCategoryUpdate,
    AsyncMemberRequestOut, PendingRequestStatusOut, SimpleGroupMemberCreate
)

router = APIRouter(prefix="/groups", tags=["groups"])

def get_current_user_id(access_token: str = Header(..., description="Access token (without Bearer)")):
    """Extract current user ID from JWT token"""
    if access_token.startswith("Bearer "):
        access_token = access_token.replace("Bearer ", "")
    user_id = get_current_user(access_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/", response_model=GroupOut)
def create_new_group(
    group_data: GroupCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new group"""
    return create_group(db, group_data, user_id)


@router.get("/", response_model=List[GroupOut])
def get_my_groups(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all groups for current user"""
    return get_user_groups(db, user_id)


@router.get("/{group_slug}", response_model=GroupWithMembers)
def get_group_details(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get group details with members"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    members = get_group_members(db, group.id)
    return GroupWithMembers(
        id=group.id,
        name=group.name,
        slug=group.slug,
        image_url=group.image_url,
        created_by=group.created_by,
        rounding_option=group.rounding_option,
        created_at=group.created_at,
        members=[GroupMemberOut(
            id=member.id,
            group_id=member.group_id,
            user_id=member.user_id,
            is_admin=member.is_admin,
            joined_at=member.joined_at
        ) for member in members]
    )


@router.patch("/{group_slug}", response_model=GroupOut)
def update_existing_group(
    group_slug: str,
    update_data: GroupUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update a group (admin only)"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return update_group(db, group.id, update_data, user_id)


@router.delete("/{group_slug}")
def delete_existing_group(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a group (admin only)"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    delete_group(db, group.id, user_id)
    return {"message": "Group deleted successfully"}


@router.post("/{group_slug}/members", response_model=Union[GroupMemberOut, AsyncMemberRequestOut])
def add_group_member(
    group_slug: str,
    member_data: SimpleGroupMemberCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Add a member to group (admin only)
    
    Request body:
    {
        "is_admin": boolean,
        "identifier": "email or phone number"
    }
    
    The backend will automatically identify if the identifier is a phone number or email.
    """
    try:
        # Convert SimpleGroupMemberCreate to GroupMemberCreate for compatibility
        # Determine if identifier is email or phone
        identifier = member_data.identifier.strip()
        
        # Simple email detection (contains @ and has valid email structure)
        is_email = "@" in identifier and "." in identifier.split("@")[-1]
        
        if is_email:
            # Convert to GroupMemberCreate with email
            group_member_data = GroupMemberCreate(
                email=identifier,
                is_admin=member_data.is_admin
            )
        else:
            # Assume it's a phone number
            group_member_data = GroupMemberCreate(
                phone=identifier,
                is_admin=member_data.is_admin
            )
        
        return add_member_to_group_enhanced(db, group_slug, group_member_data, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_slug}/members/pending/{request_id}", response_model=PendingRequestStatusOut)
def get_pending_member_request_status(
    group_slug: str,
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get the status of a pending member addition request"""
    from app.models.pending_requests import PendingMemberRequest
    from app.services.group_service import get_group_by_slug, is_group_admin
    
    # Get group by slug
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if requester is admin
    if not is_group_admin(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can check request status")
    
    # Find the pending request
    pending_request = db.query(PendingMemberRequest).filter(
        PendingMemberRequest.request_id == request_id,
        PendingMemberRequest.group_id == group.id
    ).first()
    
    if not pending_request:
        raise HTTPException(status_code=404, detail="Pending request not found")
    
    return {
        "request_id": pending_request.request_id,
        "phone_or_email": pending_request.phone_or_email,
        "status": pending_request.status,
        "error_message": pending_request.error_message,
        "created_at": pending_request.created_at,
        "updated_at": pending_request.updated_at
    }


@router.delete("/{group_slug}/members/{member_user_id}")
def remove_group_member(
    group_slug: str,
    member_user_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Remove a member from group"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    remove_member_from_group(db, group.id, member_user_id, user_id)
    return {"message": "Member removed successfully"}


@router.post("/{group_slug}/categories", response_model=GroupCategoryOut)
def create_category(
    group_slug: str,
    category_data: GroupCategoryCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a category in group (admin only)"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return create_group_category(db, group.id, category_data, user_id)


@router.get("/{group_slug}/categories", response_model=List[GroupCategoryOut])
def get_categories(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all categories for a group"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    return get_group_categories(db, group.id)


@router.patch("/{group_slug}/categories/{category_id}", response_model=GroupCategoryOut)
def update_category(
    group_slug: str,
    category_id: str,
    update_data: GroupCategoryUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update a category (admin only)"""
    return update_group_category(db, category_id, update_data, user_id)


@router.delete("/{group_slug}/categories/{category_id}")
def delete_category(
    group_slug: str,
    category_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a category (admin only)"""
    delete_group_category(db, category_id, user_id)
    return {"message": "Category deleted successfully"}
