import re
from typing import Optional
from sqlalchemy.orm import Session
from app.models.groups import Group


def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from a group name.
    Converts to lowercase, replaces spaces with hyphens, removes special characters.
    """
    if not name or not name.strip():
        # Fallback for empty names
        import uuid
        return f"group-{str(uuid.uuid4())[:8]}"

    # Convert to lowercase and strip whitespace
    slug = name.lower().strip()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)

    # Remove special characters except hyphens and alphanumeric
    slug = re.sub(r'[^\w\-]', '', slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Ensure minimum length and fallback if empty
    if not slug:
        import uuid
        return f"group-{str(uuid.uuid4())[:8]}"

    # Limit length to prevent overly long URLs
    if len(slug) > 100:
        slug = slug[:100].rstrip('-')

    return slug


def make_slug_unique(slug: str, db: Session, exclude_group_id: Optional[str] = None) -> str:
    """
    Ensure slug is unique by appending a number if necessary.
    """
    original_slug = slug
    counter = 1

    while True:
        # Check if slug exists
        query = db.query(Group).filter(Group.slug == slug)
        if exclude_group_id:
            query = query.filter(Group.id != exclude_group_id)

        existing_group = query.first()

        if not existing_group:
            return slug

        # Append counter to make it unique
        slug = f"{original_slug}-{counter}"
        counter += 1

        # Prevent infinite loops (though highly unlikely)
        if counter > 10000:
            # Ultimate fallback with timestamp
            import time
            return f"{original_slug}-{int(time.time())}"


def create_group_slug(name: str, db: Session, exclude_group_id: Optional[str] = None) -> str:
    """
    Create a unique slug for a group name.
    Always generates a slug automatically from the name.
    """
    base_slug = generate_slug(name)
    unique_slug = make_slug_unique(base_slug, db, exclude_group_id)

    # Final validation
    if not unique_slug or len(unique_slug) < 3:
        # Emergency fallback
        import uuid
        unique_slug = f"group-{str(uuid.uuid4())[:12]}"

    return unique_slug
