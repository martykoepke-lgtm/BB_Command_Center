"""
Initiative API — CRUD, phase management, and the initiative living profile.

Routes:
  GET    /api/initiatives              — List initiatives (filterable)
  POST   /api/initiatives              — Create initiative directly
  GET    /api/initiatives/{id}         — Full initiative profile
  PATCH  /api/initiatives/{id}         — Update initiative
  GET    /api/initiatives/{id}/phases  — List phases with artifacts
  PATCH  /api/initiatives/{id}/phases/{phase_name}  — Update phase status / gate review
  POST   /api/initiatives/{id}/refine  — AI-assisted initiative refinement
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.initiative import Initiative
from app.models.phase import Phase
from app.services.event_bus import INITIATIVE_COMPLETED, PHASE_ADVANCED, get_event_bus
from app.schemas.initiative import (
    InitiativeCreate,
    InitiativeList,
    InitiativeOut,
    InitiativeSummary,
    InitiativeUpdate,
    PhaseOut,
)

router = APIRouter(prefix="/initiatives", tags=["Initiatives"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_initiative_or_404(
    initiative_id: UUID, db: AsyncSession, load_phases: bool = True
) -> Initiative:
    query = select(Initiative).where(Initiative.id == initiative_id)
    if load_phases:
        query = query.options(selectinload(Initiative.phases))
    result = await db.execute(query)
    initiative = result.scalar_one_or_none()
    if initiative is None:
        raise HTTPException(status_code=404, detail=f"Initiative {initiative_id} not found")
    return initiative


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=InitiativeList)
async def list_initiatives(
    status: str | None = Query(None),
    methodology: str | None = Query(None),
    priority: str | None = Query(None),
    current_phase: str | None = Query(None),
    lead_analyst_id: UUID | None = Query(None),
    initiative_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List initiatives with filters for dashboard views."""
    query = select(Initiative)
    count_query = select(func.count(Initiative.id))

    # Apply filters
    filters = []
    if status:
        filters.append(Initiative.status == status)
    if methodology:
        filters.append(Initiative.methodology == methodology)
    if priority:
        filters.append(Initiative.priority == priority)
    if current_phase:
        filters.append(Initiative.current_phase == current_phase)
    if lead_analyst_id:
        filters.append(Initiative.lead_analyst_id == lead_analyst_id)
    if initiative_type:
        filters.append(Initiative.initiative_type == initiative_type)

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Initiative.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return InitiativeList(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=InitiativeOut, status_code=201)
async def create_initiative(
    payload: InitiativeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new initiative directly (without going through request intake)."""
    count_result = await db.execute(select(func.count(Initiative.id)))
    count = count_result.scalar_one()
    initiative_number = f"INI-{count + 1:04d}"

    initiative = Initiative(
        initiative_number=initiative_number,
        request_id=payload.request_id,
        title=payload.title,
        problem_statement=payload.problem_statement,
        desired_outcome=payload.desired_outcome,
        scope=payload.scope,
        out_of_scope=payload.out_of_scope,
        business_case=payload.business_case,
        methodology=payload.methodology,
        initiative_type=payload.initiative_type,
        priority=payload.priority,
        lead_analyst_id=payload.lead_analyst_id,
        team_id=payload.team_id,
        sponsor_id=payload.sponsor_id,
        start_date=payload.start_date,
        target_completion=payload.target_completion,
        projected_savings=payload.projected_savings,
        projected_impact=payload.projected_impact,
        tags=payload.tags,
    )
    # For non-initiative work types, override methodology and current_phase
    if payload.initiative_type in ("consultation", "work_assignment"):
        initiative.methodology = "none"
        initiative.current_phase = "active"

    db.add(initiative)
    await db.flush()

    # Only create methodology phases for "initiative" work type
    if payload.initiative_type not in ("consultation", "work_assignment"):
        if payload.methodology == "DMAIC":
            phase_names = ["define", "measure", "analyze", "improve", "control"]
        elif payload.methodology == "A3":
            phase_names = ["background", "current_condition", "goal", "root_cause", "countermeasures", "implementation", "follow_up"]
        elif payload.methodology == "PDSA":
            phase_names = ["plan", "do", "study", "act"]
        elif payload.methodology == "Kaizen":
            phase_names = ["prepare", "execute", "sustain"]
        else:
            phase_names = ["define", "measure", "analyze", "improve", "control"]

        for order, name in enumerate(phase_names, start=1):
            phase = Phase(
                initiative_id=initiative.id,
                phase_name=name,
                phase_order=order,
                status="in_progress" if order == 1 else "not_started",
            )
            db.add(phase)

    await db.flush()
    await db.refresh(initiative, ["phases"])
    return initiative


@router.get("/{initiative_id}", response_model=InitiativeOut)
async def get_initiative(
    initiative_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the full initiative profile including phases."""
    return await _get_initiative_or_404(initiative_id, db)


@router.patch("/{initiative_id}", response_model=InitiativeOut)
async def update_initiative(
    initiative_id: UUID,
    payload: InitiativeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update initiative fields."""
    initiative = await _get_initiative_or_404(initiative_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(initiative, field, value)

    initiative.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(initiative, ["phases"])
    return initiative


@router.get("/{initiative_id}/phases", response_model=list[PhaseOut])
async def list_phases(
    initiative_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all phases for an initiative."""
    initiative = await _get_initiative_or_404(initiative_id, db)
    return initiative.phases


@router.patch("/{initiative_id}/phases/{phase_name}", response_model=PhaseOut)
async def update_phase(
    initiative_id: UUID,
    phase_name: str,
    status: str | None = Query(None),
    gate_approved: bool | None = Query(None),
    gate_notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a phase's status or gate approval.
    When a phase is completed and the next phase exists, auto-advance the initiative.
    """
    result = await db.execute(
        select(Phase).where(
            Phase.initiative_id == initiative_id,
            Phase.phase_name == phase_name,
        )
    )
    phase = result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail=f"Phase '{phase_name}' not found for this initiative")

    if status:
        phase.status = status
        if status == "in_progress" and phase.started_at is None:
            phase.started_at = datetime.now(timezone.utc)
        elif status == "completed":
            phase.completed_at = datetime.now(timezone.utc)

    if gate_approved is not None:
        phase.gate_approved = gate_approved
    if gate_notes is not None:
        phase.gate_notes = gate_notes

    await db.flush()

    # Auto-advance: if phase completed, start next phase and update initiative current_phase
    if status == "completed":
        next_result = await db.execute(
            select(Phase).where(
                Phase.initiative_id == initiative_id,
                Phase.phase_order == phase.phase_order + 1,
            )
        )
        next_phase = next_result.scalar_one_or_none()
        if next_phase:
            next_phase.status = "in_progress"
            next_phase.started_at = datetime.now(timezone.utc)

            # Update initiative's current_phase
            init_result = await db.execute(
                select(Initiative).where(Initiative.id == initiative_id)
            )
            initiative = init_result.scalar_one()
            initiative.current_phase = next_phase.phase_name
            initiative.updated_at = datetime.now(timezone.utc)
        else:
            # All phases complete — mark initiative as completed
            init_result = await db.execute(
                select(Initiative).where(Initiative.id == initiative_id)
            )
            initiative = init_result.scalar_one()
            initiative.status = "completed"
            initiative.current_phase = "complete"
            initiative.updated_at = datetime.now(timezone.utc)

        await db.flush()

        # Publish workflow events
        try:
            bus = get_event_bus()
            if next_phase:
                await bus.publish(PHASE_ADVANCED, {
                    "initiative_id": str(initiative_id),
                    "completed_phase": phase_name,
                    "next_phase": next_phase.phase_name,
                })
            else:
                # Initiative completed
                await bus.publish(PHASE_ADVANCED, {
                    "initiative_id": str(initiative_id),
                    "completed_phase": phase_name,
                    "next_phase": "complete",
                })
                await bus.publish(INITIATIVE_COMPLETED, {
                    "initiative_id": str(initiative_id),
                })
        except RuntimeError:
            pass  # EventBus not initialized (e.g., in tests)

    await db.refresh(phase)
    return phase


# ---------------------------------------------------------------------------
# AI Refinement
# ---------------------------------------------------------------------------

class RefineRequest(BaseModel):
    """Input for the AI refinement conversation."""
    message: str = Field("", max_length=10000)
    conversation_history: list[dict] = Field(default_factory=list)


class RefineResponse(BaseModel):
    """AI refinement response."""
    content: str
    suggestions: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    conversation_history: list[dict] = Field(default_factory=list)


@router.post("/{initiative_id}/refine", response_model=RefineResponse)
async def refine_initiative(
    initiative_id: UUID,
    payload: RefineRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    AI-assisted initiative refinement — uses the Triage agent to ask
    probing questions and suggest improvements to strengthen the business case.
    """
    initiative = await _get_initiative_or_404(initiative_id, db)

    # Lazy imports to avoid circular dependency and to fail gracefully
    try:
        from app.agents.base import AgentContext, AgentType
        from app.main import get_orchestrator

        orchestrator = get_orchestrator()
    except Exception:
        return RefineResponse(
            content="AI refinement is not available. Please check that the ANTHROPIC_API_KEY is configured.",
            suggestions=[],
            metadata={},
            conversation_history=payload.conversation_history,
        )

    # Build rich context from the initiative
    context = AgentContext(
        initiative_id=initiative.id,
        initiative_title=initiative.title,
        problem_statement=initiative.problem_statement,
        desired_outcome=initiative.desired_outcome,
        methodology=initiative.methodology,
        current_phase=initiative.current_phase,
        initiative_status=initiative.status,
        initiative_priority=initiative.priority,
        conversation_history=payload.conversation_history,
        extra={
            "scope": initiative.scope or "",
            "business_case": initiative.business_case or "",
            "initiative_type": initiative.initiative_type or "initiative",
        },
    )

    # Construct the user message
    if payload.message.strip():
        user_message = payload.message
    else:
        # Initial call — ask AI to review and probe
        user_message = (
            "Review this initiative and ask 3-5 probing questions to help strengthen "
            "the business case, problem statement, and desired outcome. "
            "Be specific and constructive. If fields like scope or business_case "
            "are empty, suggest concrete content for them."
        )

    response = await orchestrator.invoke_specific(AgentType.TRIAGE, user_message, context)

    # Build updated history
    updated_history = list(payload.conversation_history)
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": response.content})

    return RefineResponse(
        content=response.content,
        suggestions=response.suggestions,
        metadata=response.metadata,
        conversation_history=updated_history,
    )
