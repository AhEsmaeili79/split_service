from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from typing import List, Optional
from app.models.groups import Group, GroupMember, GroupCategory
from app.schemas.group_schema import (
    GroupCreate, GroupUpdate, GroupOut, GroupMemberCreate,
    GroupMemberOut, GroupCategoryCreate, GroupCategoryOut, GroupCategoryUpdate
)
from app.utils.slug_utils import create_group_slug


def create_group(db: Session, group_data: GroupCreate, created_by: str) -> Group:
    """Create a new group with auto-generated unique slug"""
    # Always generate slug automatically from group name
    slug = create_group_slug(group_data.name, db)

    group = Group(
        name=group_data.name,
        slug=slug,
        image_url=group_data.image_url,
        created_by=created_by,
        rounding_option=group_data.rounding_option
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    # Add creator as admin member
    add_member_to_group(db, group.id, created_by, is_admin=True)
    return group


def get_group(db: Session, group_id: str) -> Optional[Group]:
    """Get a group by ID"""
    return db.query(Group).filter(Group.id == group_id).first()


def get_group_by_slug(db: Session, slug: str) -> Optional[Group]:
    """Get a group by slug"""
    return db.query(Group).filter(Group.slug == slug).first()


def get_user_groups(db: Session, user_id: str) -> List[Group]:
    """Get all groups for a user"""
    return db.query(Group).join(GroupMember).filter(GroupMember.user_id == user_id).all()


def update_group(db: Session, group_id: str, update_data: GroupUpdate, user_id: str) -> Group:
    """Update a group (admin only)"""
    group = get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if user is admin
    if not is_group_admin(db, group_id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can update group")

    # If name is being updated, regenerate slug from new name
    if update_data.name and update_data.name != group.name:
        new_slug = create_group_slug(update_data.name, db, group_id)
        group.slug = new_slug

    # Update other fields (excluding slug as it's auto-generated)
    for field, value in update_data.dict(exclude_unset=True).items():
        if field != 'slug':  # Never allow manual slug updates
            setattr(group, field, value)

    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: str, user_id: str):
    """Delete a group (admin only)"""
    group = get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not is_group_admin(db, group_id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can delete group")

    db.delete(group)
    db.commit()


def add_member_to_group(db: Session, group_id: str, user_id: str, is_admin: bool = False):
    """Add a member to a group"""
    # Check if already a member
    existing = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this group")

    member = GroupMember(
        group_id=group_id,
        user_id=user_id,
        is_admin=is_admin
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member_from_group(db: Session, group_id: str, user_id: str, remover_id: str):
    """Remove a member from a group"""
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Only admins can remove others, users can remove themselves
    if user_id != remover_id and not is_group_admin(db, group_id, remover_id):
        raise HTTPException(status_code=403, detail="Only group admins can remove other members")

    db.delete(member)
    db.commit()


def is_group_admin(db: Session, group_id: str, user_id: str) -> bool:
    """Check if user is admin of the group"""
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    ).first()
    return member and member.is_admin


def is_group_member(db: Session, group_id: str, user_id: str) -> bool:
    """Check if user is member of the group"""
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    ).first()
    return member is not None


def get_group_members(db: Session, group_id: str) -> List[GroupMember]:
    """Get all members of a group"""
    return db.query(GroupMember).filter(GroupMember.group_id == group_id).all()


def create_group_category(db: Session, group_id: str, category_data: GroupCategoryCreate, user_id: str) -> GroupCategory:
    """Create a category in a group (admin only)"""
    if not is_group_admin(db, group_id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can create categories")

    # Check if slug is unique within the group
    existing = db.query(GroupCategory).filter(
        and_(GroupCategory.group_id == group_id, GroupCategory.slug == category_data.slug)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Category slug must be unique within the group")

    category = GroupCategory(
        group_id=group_id,
        name=category_data.name,
        slug=category_data.slug
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_group_categories(db: Session, group_id: str) -> List[GroupCategory]:
    """Get all categories for a group"""
    return db.query(GroupCategory).filter(GroupCategory.group_id == group_id).all()


def update_group_category(db: Session, category_id: str, update_data: GroupCategoryUpdate, user_id: str) -> GroupCategory:
    """Update a group category (admin only)"""
    category = db.query(GroupCategory).filter(GroupCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if not is_group_admin(db, category.group_id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can update categories")

    # Check slug uniqueness if being updated
    if update_data.slug:
        existing = db.query(GroupCategory).filter(
            and_(
                GroupCategory.group_id == category.group_id,
                GroupCategory.slug == update_data.slug,
                GroupCategory.id != category_id
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category slug must be unique within the group")

    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_group_category(db: Session, category_id: str, user_id: str):
    """Delete a group category (admin only)"""
    category = db.query(GroupCategory).filter(GroupCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if not is_group_admin(db, category.group_id, user_id):
        raise HTTPException(status_code=403, detail="Only group admins can delete categories")

    db.delete(category)
    db.commit()
