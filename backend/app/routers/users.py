"""
User management API — list, update, and view workload.

Routes:
  GET    /api/users              — List users (admin/manager only)
  GET    /api/users/{id}         — Get single user profile
  PATCH  /api/users/{id}         — Update user (admin or self)
  GET    /api/users/{id}/workload — Workload allocation summary
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.initiative import Initiative
from app.models.supporting import WorkloadEntry
from app.schemas.user import UserList, UserOut, UserUpdate, UserWorkload

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserList)
async def list_users(
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Requires admin or manager role."""
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return UserList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a user profile by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user profile.
    Users can update their own profile. Admins can update anyone.
    Only admins can change role or is_active.
    """
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Non-admins cannot change role or deactivate accounts
    if current_user.role != "admin":
        update_data.pop("role", None)
        update_data.pop("is_active", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/{user_id}/workload", response_model=UserWorkload)
async def get_user_workload(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a user's workload summary for the current week.
    Shows capacity, allocation, utilization, and active initiative count.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Current week (Monday)
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    # Sum allocated hours this week
    hours_result = await db.execute(
        select(func.coalesce(func.sum(WorkloadEntry.hours_allocated), 0))
        .where(WorkloadEntry.user_id == user_id)
        .where(WorkloadEntry.week_of == monday)
    )
    allocated = float(hours_result.scalar_one())

    # Count active initiatives where user is lead analyst
    init_count_result = await db.execute(
        select(func.count(Initiative.id))
        .where(Initiative.lead_analyst_id == user_id)
        .where(Initiative.status == "active")
    )
    active_initiatives = init_count_result.scalar_one()

    capacity = float(user.capacity_hours or 40)
    utilization = (allocated / capacity * 100) if capacity > 0 else 0

    return UserWorkload(
        id=user.id,
        full_name=user.full_name,
        role=user.role,
        capacity_hours=capacity,
        allocated_hours=allocated,
        utilization_pct=round(utilization, 1),
        active_initiatives=active_initiatives,
    )
