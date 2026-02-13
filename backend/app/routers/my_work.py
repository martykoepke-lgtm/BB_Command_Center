"""
My Work — aggregate personal workspace endpoint.

Returns the current user's assigned initiatives, action items, and stats
in a single call so the frontend can render the personal workspace quickly.

Routes:
  GET /api/my-work  — aggregated personal work view
"""

from __future__ import annotations

from datetime import date, timedelta, timezone, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.initiative import Initiative
from app.models.supporting import ActionItem
from app.schemas.my_work import (
    MyActionItem,
    MyInitiativeSummary,
    MyWorkResponse,
    MyWorkStats,
)

router = APIRouter(prefix="/my-work", tags=["My Work"])


@router.get("", response_model=MyWorkResponse)
async def get_my_work(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated work for the authenticated user."""
    user_id = current_user.id
    today = date.today()
    week_end = today + timedelta(days=7)

    # ---- My Initiatives (where I'm lead analyst, still active) ----
    init_query = (
        select(Initiative)
        .where(
            Initiative.lead_analyst_id == user_id,
            Initiative.status.in_(["active", "on_hold"]),
        )
        .order_by(Initiative.created_at.desc())
    )
    init_result = await db.execute(init_query)
    my_initiatives = init_result.scalars().all()

    # ---- My Action Items (assigned to me, not completed/cancelled) ----
    action_query = (
        select(ActionItem, Initiative.initiative_number, Initiative.title)
        .join(Initiative, ActionItem.initiative_id == Initiative.id)
        .where(
            ActionItem.assigned_to == user_id,
            ActionItem.status.notin_(["completed", "cancelled"]),
        )
        .order_by(ActionItem.due_date.asc().nullslast(), ActionItem.created_at.desc())
    )
    action_result = await db.execute(action_query)
    action_rows = action_result.all()

    # Build action items with initiative context
    my_actions: list[MyActionItem] = []
    overdue_count = 0
    due_this_week_count = 0

    for action, init_number, init_title in action_rows:
        if action.due_date and action.due_date < today:
            overdue_count += 1
        elif action.due_date and action.due_date <= week_end:
            due_this_week_count += 1

        my_actions.append(
            MyActionItem(
                id=action.id,
                initiative_id=action.initiative_id,
                initiative_number=init_number,
                initiative_title=init_title,
                title=action.title,
                description=action.description,
                status=action.status,
                priority=action.priority,
                due_date=action.due_date,
                completed_at=action.completed_at,
                created_at=action.created_at,
            )
        )

    stats = MyWorkStats(
        active_initiatives=len([i for i in my_initiatives if i.status == "active"]),
        open_actions=len(my_actions),
        overdue_actions=overdue_count,
        due_this_week=due_this_week_count,
    )

    return MyWorkResponse(
        stats=stats,
        initiatives=[MyInitiativeSummary.model_validate(i) for i in my_initiatives],
        actions=my_actions,
    )
