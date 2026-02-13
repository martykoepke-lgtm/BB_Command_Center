"""
Team management API — CRUD, member management, workload overview.

Routes:
  GET    /api/teams              — List teams
  POST   /api/teams              — Create team (admin/manager)
  GET    /api/teams/{id}         — Get team detail
  PATCH  /api/teams/{id}         — Update team
  DELETE /api/teams/{id}         — Delete team (admin/manager)
  GET    /api/teams/{id}/members — List team members
  POST   /api/teams/{id}/members — Add member to team (JSON body)
  DELETE /api/teams/{id}/members/{user_id} — Remove member
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import Team, User, team_members
from app.schemas.user import TeamCreate, TeamList, TeamMemberOut, TeamOut, TeamUpdate


class AddMemberBody(BaseModel):
    """Request body for adding a member to a team."""
    user_id: UUID
    role_in_team: str = "member"

router = APIRouter(prefix="/teams", tags=["Teams"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_team_or_404(team_id: UUID, db: AsyncSession) -> Team:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


async def _team_with_count(team: Team, db: AsyncSession) -> TeamOut:
    """Build TeamOut with member_count."""
    count_result = await db.execute(
        select(func.count()).select_from(team_members).where(team_members.c.team_id == team.id)
    )
    count = count_result.scalar_one()
    return TeamOut(
        id=team.id,
        name=team.name,
        description=team.description,
        department=team.department,
        organization=team.organization,
        manager_id=team.manager_id,
        created_at=team.created_at,
        member_count=count,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=TeamList)
async def list_teams(
    department: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all teams."""
    query = select(Team)
    count_query = select(func.count(Team.id))

    if department:
        query = query.where(Team.department == department)
        count_query = count_query.where(Team.department == department)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Team.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    teams = result.scalars().all()

    items = [await _team_with_count(t, db) for t in teams]
    return TeamList(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TeamOut, status_code=201)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team. Requires admin or manager role."""
    team = Team(
        name=payload.name,
        description=payload.description,
        department=payload.department,
        organization=payload.organization,
        manager_id=payload.manager_id,
    )
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return await _team_with_count(team, db)


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a team by ID."""
    team = await _get_team_or_404(team_id, db)
    return await _team_with_count(team, db)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Update team details."""
    team = await _get_team_or_404(team_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    await db.flush()
    await db.refresh(team)
    return await _team_with_count(team, db)


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a team and remove all member associations."""
    team = await _get_team_or_404(team_id, db)
    # Remove all member associations first
    await db.execute(
        delete(team_members).where(team_members.c.team_id == team_id)
    )
    await db.delete(team)
    await db.flush()


@router.get("/{team_id}/members", response_model=list[TeamMemberOut])
async def list_team_members(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of a team."""
    await _get_team_or_404(team_id, db)

    result = await db.execute(
        select(
            User.id.label("user_id"),
            User.full_name,
            User.email,
            User.role,
            team_members.c.role_in_team,
        )
        .join(team_members, team_members.c.user_id == User.id)
        .where(team_members.c.team_id == team_id)
        .order_by(User.full_name)
    )
    rows = result.all()
    return [
        TeamMemberOut(
            user_id=r.user_id,
            full_name=r.full_name,
            email=r.email,
            role=r.role,
            role_in_team=r.role_in_team or "member",
        )
        for r in rows
    ]


@router.post("/{team_id}/members", status_code=201)
async def add_team_member(
    team_id: UUID,
    payload: AddMemberBody,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to a team. Accepts JSON body with user_id and role_in_team."""
    await _get_team_or_404(team_id, db)

    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = await db.execute(
        select(team_members)
        .where(team_members.c.team_id == team_id)
        .where(team_members.c.user_id == payload.user_id)
    )
    if existing.first() is not None:
        raise HTTPException(status_code=409, detail="User is already a member of this team")

    await db.execute(
        insert(team_members).values(
            team_id=team_id, user_id=payload.user_id, role_in_team=payload.role_in_team
        )
    )
    await db.flush()
    return {"status": "added", "team_id": str(team_id), "user_id": str(payload.user_id)}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from a team."""
    result = await db.execute(
        delete(team_members)
        .where(team_members.c.team_id == team_id)
        .where(team_members.c.user_id == user_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found in this team")
    await db.flush()
