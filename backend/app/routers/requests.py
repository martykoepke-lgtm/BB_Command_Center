"""
Request intake API — submit, review, triage, and convert improvement requests.

Routes:
  POST   /api/requests           — Submit a new request
  GET    /api/requests           — List requests (filterable by status)
  GET    /api/requests/{id}      — Get single request
  PATCH  /api/requests/{id}      — Update request (review, score, etc.)
  POST   /api/requests/{id}/triage  — Run AI triage on a request
  POST   /api/requests/{id}/convert — Convert accepted request to initiative
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.request import Request
from app.models.initiative import Initiative
from app.models.phase import Phase
from app.models.user import User
from app.agents.base import AgentContext, AgentType
from app.schemas.request import RequestCreate, RequestList, RequestOut, RequestUpdate
from app.schemas.initiative import InitiativeOut

router = APIRouter(prefix="/requests", tags=["Requests"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _next_request_number(db: AsyncSession) -> str:
    """Generate the next sequential request number (REQ-0001, REQ-0002, ...)."""
    result = await db.execute(select(func.count(Request.id)))
    count = result.scalar_one()
    return f"REQ-{count + 1:04d}"


async def _get_request_or_404(request_id: UUID, db: AsyncSession) -> Request:
    result = await db.execute(select(Request).where(Request.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    return req


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=RequestOut, status_code=201)
async def create_request(
    payload: RequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a new improvement request."""
    req = Request(
        request_number=await _next_request_number(db),
        title=payload.title,
        description=payload.description,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        requester_dept=payload.requester_dept,
        problem_statement=payload.problem_statement,
        desired_outcome=payload.desired_outcome,
        business_impact=payload.business_impact,
        urgency=payload.urgency,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


@router.get("", response_model=RequestList)
async def list_requests(
    status: str | None = Query(None, description="Filter by status"),
    urgency: str | None = Query(None, description="Filter by urgency"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List improvement requests with optional filters."""
    query = select(Request)
    count_query = select(func.count(Request.id))

    if status:
        query = query.where(Request.status == status)
        count_query = count_query.where(Request.status == status)
    if urgency:
        query = query.where(Request.urgency == urgency)
        count_query = count_query.where(Request.urgency == urgency)

    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    query = query.order_by(Request.submitted_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return RequestList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{request_id}", response_model=RequestOut)
async def get_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single request by ID."""
    return await _get_request_or_404(request_id, db)


@router.patch("/{request_id}", response_model=RequestOut)
async def update_request(
    request_id: UUID,
    payload: RequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a request (e.g., during review)."""
    req = await _get_request_or_404(request_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)

    # If status is changing to reviewed states, stamp the timestamp
    if payload.status and payload.status in ("accepted", "declined", "under_review"):
        req.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(req)
    return req


@router.post("/{request_id}/convert", response_model=InitiativeOut, status_code=201)
async def convert_to_initiative(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Convert an accepted request into a full initiative.
    Creates the initiative and its 5 DMAIC phases automatically.
    """
    req = await _get_request_or_404(request_id, db)

    if req.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail=f"Request must be 'accepted' to convert. Current status: {req.status}",
        )
    if req.converted_initiative_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Request has already been converted to an initiative",
        )

    # Generate initiative number
    count_result = await db.execute(select(func.count(Initiative.id)))
    count = count_result.scalar_one()
    initiative_number = f"INI-{count + 1:04d}"

    # Create initiative from request data
    initiative = Initiative(
        initiative_number=initiative_number,
        request_id=req.id,
        title=req.title,
        problem_statement=req.problem_statement or req.description or "",
        desired_outcome=req.desired_outcome or "",
        methodology=req.recommended_methodology or "DMAIC",
        priority=req.urgency,
    )
    db.add(initiative)
    await db.flush()

    # Create the 5 DMAIC phases
    phase_names = ["define", "measure", "analyze", "improve", "control"]
    for order, name in enumerate(phase_names, start=1):
        phase = Phase(
            initiative_id=initiative.id,
            phase_name=name,
            phase_order=order,
            status="in_progress" if name == "define" else "not_started",
        )
        db.add(phase)

    # Link request back to initiative
    req.converted_initiative_id = initiative.id
    req.status = "converted"

    await db.flush()
    await db.refresh(initiative, ["phases"])
    return initiative


@router.post("/{request_id}/triage")
async def triage_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run AI triage on a request.
    The Triage Agent analyzes the problem statement, scores complexity,
    recommends methodology, and suggests key questions.
    """
    req = await _get_request_or_404(request_id, db)

    from app.main import get_orchestrator
    orchestrator = get_orchestrator()

    # Build context for the triage agent
    context = AgentContext(
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
    )

    # Compose the triage prompt from request data
    triage_prompt = (
        f"Please triage this new improvement request:\n\n"
        f"**Title:** {req.title}\n"
        f"**Description:** {req.description or 'Not provided'}\n"
        f"**Problem Statement:** {req.problem_statement or 'Not provided'}\n"
        f"**Desired Outcome:** {req.desired_outcome or 'Not provided'}\n"
        f"**Business Impact:** {req.business_impact or 'Not provided'}\n"
        f"**Urgency:** {req.urgency}\n"
        f"**Requester:** {req.requester_name} ({req.requester_dept or 'Unknown dept'})\n"
    )

    # Invoke triage agent directly (bypass routing)
    response = await orchestrator.invoke_specific(AgentType.TRIAGE, triage_prompt, context)

    # Update request with AI assessment
    if response.metadata:
        if "complexity_score" in response.metadata:
            req.complexity_score = response.metadata["complexity_score"]
        if "recommended_methodology" in response.metadata:
            req.recommended_methodology = response.metadata["recommended_methodology"]
    req.status = "under_review"
    req.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(req)

    return {
        "request": RequestOut.model_validate(req),
        "triage_assessment": {
            "agent_type": response.agent_type,
            "content": response.content,
            "suggestions": response.suggestions,
            "metadata": response.metadata,
        },
    }
