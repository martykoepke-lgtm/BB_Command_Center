"""
Assignment Engine — workload balancing and skill-based initiative assignment.

Handles:
- Recommending analysts for new initiatives based on skills and capacity
- Calculating team utilization
- Flagging overloaded team members
- Balancing workload across teams
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.initiative import Initiative
from app.models.user import User, team_members
from app.models.supporting import WorkloadEntry


async def get_analyst_workload(
    user_id: UUID,
    week_of: date | None,
    db: AsyncSession,
) -> dict:
    """
    Get an analyst's workload for a given week.

    Returns:
        {
            "user_id": "...",
            "full_name": "...",
            "capacity_hours": 40,
            "allocated_hours": 28,
            "utilization_pct": 70.0,
            "active_initiative_count": 3,
            "initiatives": [{"id": "...", "title": "...", "hours": 8}, ...]
        }
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        return {"error": "User not found"}

    if week_of is None:
        today = date.today()
        week_of = today - timedelta(days=today.weekday())  # Monday

    # Get workload entries for this week
    entries_result = await db.execute(
        select(WorkloadEntry, Initiative.title)
        .outerjoin(Initiative, Initiative.id == WorkloadEntry.initiative_id)
        .where(WorkloadEntry.user_id == user_id)
        .where(WorkloadEntry.week_of == week_of)
    )
    entries = entries_result.all()

    allocated = sum(float(e[0].hours_allocated) for e in entries)
    capacity = float(user.capacity_hours or 40)
    utilization = (allocated / capacity * 100) if capacity > 0 else 0

    # Active initiatives
    init_count_result = await db.execute(
        select(func.count(Initiative.id))
        .where(Initiative.lead_analyst_id == user_id)
        .where(Initiative.status == "active")
    )
    active_count = init_count_result.scalar_one()

    return {
        "user_id": str(user.id),
        "full_name": user.full_name,
        "capacity_hours": capacity,
        "allocated_hours": allocated,
        "utilization_pct": round(utilization, 1),
        "active_initiative_count": active_count,
        "initiatives": [
            {
                "id": str(e[0].initiative_id) if e[0].initiative_id else None,
                "title": e[1] or "Unlinked",
                "hours": float(e[0].hours_allocated),
            }
            for e in entries
        ],
    }


async def recommend_analyst(
    required_skills: list[str],
    team_id: UUID | None,
    db: AsyncSession,
) -> list[dict]:
    """
    Recommend analysts for a new initiative based on skills and capacity.

    Scoring:
    - Skill match: +10 per matching skill
    - Availability: higher score for lower utilization
    - Active initiatives: penalty for high initiative count

    Returns ranked list of candidates:
        [{"user_id": "...", "full_name": "...", "score": 85, "reasons": [...]}]
    """
    # Get eligible analysts
    query = select(User).where(User.role.in_(["analyst", "manager"]), User.is_active == True)

    if team_id:
        query = query.join(team_members, team_members.c.user_id == User.id).where(
            team_members.c.team_id == team_id
        )

    result = await db.execute(query)
    analysts = result.scalars().all()

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    candidates = []
    for analyst in analysts:
        score = 0
        reasons = []

        # Skill match scoring
        user_skills = set(s.lower() for s in (analyst.skills or []))
        matched = [s for s in required_skills if s.lower() in user_skills]
        skill_score = len(matched) * 10
        score += skill_score
        if matched:
            reasons.append(f"Skill match: {', '.join(matched)} ({skill_score}pts)")

        # Utilization scoring (lower utilization = higher score)
        hours_result = await db.execute(
            select(func.coalesce(func.sum(WorkloadEntry.hours_allocated), 0))
            .where(WorkloadEntry.user_id == analyst.id)
            .where(WorkloadEntry.week_of == monday)
        )
        allocated = float(hours_result.scalar_one())
        capacity = float(analyst.capacity_hours or 40)
        utilization = (allocated / capacity * 100) if capacity > 0 else 0
        availability_score = max(0, int((100 - utilization) / 2))
        score += availability_score
        reasons.append(f"Utilization: {utilization:.0f}% ({availability_score}pts)")

        # Active initiative penalty
        init_count_result = await db.execute(
            select(func.count(Initiative.id))
            .where(Initiative.lead_analyst_id == analyst.id)
            .where(Initiative.status == "active")
        )
        active_count = init_count_result.scalar_one()
        init_penalty = active_count * 5
        score -= init_penalty
        if active_count > 0:
            reasons.append(f"Active initiatives: {active_count} (-{init_penalty}pts)")

        candidates.append({
            "user_id": str(analyst.id),
            "full_name": analyst.full_name,
            "role": analyst.role,
            "score": max(0, score),
            "utilization_pct": round(utilization, 1),
            "active_initiatives": active_count,
            "reasons": reasons,
        })

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


async def get_team_utilization(
    team_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Get utilization summary for all members of a team.

    Returns:
        {
            "team_id": "...",
            "average_utilization": 65.5,
            "members": [{"user_id": "...", "full_name": "...", "utilization_pct": 70.0, ...}],
            "overloaded": ["user_id_1"],
            "available": ["user_id_2"]
        }
    """
    # Get team members
    members_result = await db.execute(
        select(User)
        .join(team_members, team_members.c.user_id == User.id)
        .where(team_members.c.team_id == team_id)
    )
    members = members_result.scalars().all()

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    member_data = []
    overloaded = []
    available = []
    total_util = 0

    for member in members:
        hours_result = await db.execute(
            select(func.coalesce(func.sum(WorkloadEntry.hours_allocated), 0))
            .where(WorkloadEntry.user_id == member.id)
            .where(WorkloadEntry.week_of == monday)
        )
        allocated = float(hours_result.scalar_one())
        capacity = float(member.capacity_hours or 40)
        util = (allocated / capacity * 100) if capacity > 0 else 0
        total_util += util

        member_info = {
            "user_id": str(member.id),
            "full_name": member.full_name,
            "capacity_hours": capacity,
            "allocated_hours": allocated,
            "utilization_pct": round(util, 1),
        }
        member_data.append(member_info)

        if util > 90:
            overloaded.append(str(member.id))
        elif util < 60:
            available.append(str(member.id))

    avg_util = (total_util / len(members)) if members else 0

    return {
        "team_id": str(team_id),
        "member_count": len(members),
        "average_utilization": round(avg_util, 1),
        "members": member_data,
        "overloaded": overloaded,
        "available": available,
    }
