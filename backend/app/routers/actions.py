"""
Action items API — initiative-scoped and global action lists.

Routes:
  GET    /api/initiatives/{id}/actions  — List actions for initiative
  POST   /api/initiatives/{id}/actions  — Create action item
  GET    /api/actions                   — Global action list (cross-initiative)
  GET    /api/actions/{id}              — Get single action item
  POST   /api/actions                   — Create action (initiative_id in body)
  PATCH  /api/actions/{id}              — Update action item
  DELETE /api/actions/{id}              — Delete action item
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supporting import ActionItem
from app.schemas.supporting import ActionItemCreate, ActionItemList, ActionItemOut, ActionItemUpdate
from app.services.event_bus import ACTION_ASSIGNED, get_event_bus

router = APIRouter(tags=["Action Items"])


async def _publish_action_assigned(action: ActionItem) -> None:
    """Publish ACTION_ASSIGNED event if the action has an assignee."""
    if not action.assigned_to:
        return
    try:
        bus = get_event_bus()
        await bus.publish(ACTION_ASSIGNED, {
            "action_id": str(action.id),
            "initiative_id": str(action.initiative_id) if action.initiative_id else None,
            "assigned_to": str(action.assigned_to),
        })
    except RuntimeError:
        pass  # EventBus not initialized (e.g., in tests)


class ActionItemGlobalCreate(ActionItemCreate):
    """Extends ActionItemCreate to include initiative_id for the global POST endpoint."""
    initiative_id: UUID


@router.get("/initiatives/{initiative_id}/actions", response_model=list[ActionItemOut])
async def list_initiative_actions(
    initiative_id: UUID,
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all action items for an initiative."""
    query = select(ActionItem).where(ActionItem.initiative_id == initiative_id)
    if status:
        query = query.where(ActionItem.status == status)
    query = query.order_by(ActionItem.due_date.asc().nullslast(), ActionItem.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/actions", response_model=ActionItemOut, status_code=201)
async def create_action(
    initiative_id: UUID,
    payload: ActionItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an action item for an initiative."""
    action = ActionItem(
        initiative_id=initiative_id,
        phase_id=payload.phase_id,
        title=payload.title,
        description=payload.description,
        classification=payload.classification,
        assigned_to=payload.assigned_to,
        owner_name=payload.owner_name,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(action)
    await db.flush()
    await db.refresh(action)
    await _publish_action_assigned(action)
    return action


@router.get("/actions", response_model=ActionItemList)
async def list_all_actions(
    status: str | None = Query(None),
    assigned_to: UUID | None = Query(None),
    priority: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Global action list across all initiatives (paginated)."""
    query = select(ActionItem)
    if status:
        query = query.where(ActionItem.status == status)
    if assigned_to:
        query = query.where(ActionItem.assigned_to == assigned_to)
    if priority:
        query = query.where(ActionItem.priority == priority)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(ActionItem.due_date.asc().nullslast(), ActionItem.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ActionItemList(items=items, total=total, page=page, page_size=page_size)


@router.get("/actions/{action_id}", response_model=ActionItemOut)
async def get_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single action item by ID."""
    result = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    return action


@router.post("/actions", response_model=ActionItemOut, status_code=201)
async def create_action_global(
    payload: ActionItemGlobalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an action item with initiative_id in the request body."""
    action = ActionItem(
        initiative_id=payload.initiative_id,
        phase_id=payload.phase_id,
        title=payload.title,
        description=payload.description,
        classification=payload.classification,
        assigned_to=payload.assigned_to,
        owner_name=payload.owner_name,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(action)
    await db.flush()
    await db.refresh(action)
    await _publish_action_assigned(action)
    return action


@router.patch("/actions/{action_id}", response_model=ActionItemOut)
async def update_action(
    action_id: UUID,
    payload: ActionItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an action item."""
    result = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=404, detail="Action item not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Auto-set completed_at when status changes to completed
    if update_data.get("status") == "completed" and action.status != "completed":
        action.completed_at = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(action, field, value)

    await db.flush()
    await db.refresh(action)
    return action


@router.delete("/actions/{action_id}", status_code=204)
async def delete_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an action item."""
    result = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    await db.delete(action)
    await db.flush()
