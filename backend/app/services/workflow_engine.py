"""
Workflow Engine — manages initiative lifecycle, phase transitions, and gate approvals.

This is the business logic layer that enforces DMAIC methodology rules:
- Valid phase transitions (no skipping phases)
- Gate approval prerequisites
- Automatic phase setup on initiative creation
- Status validation and enforcement
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.initiative import Initiative
from app.models.phase import Phase, PhaseArtifact

# ---------------------------------------------------------------------------
# Phase ordering by methodology
# ---------------------------------------------------------------------------

METHODOLOGY_PHASES: dict[str, list[str]] = {
    "DMAIC": ["define", "measure", "analyze", "improve", "control"],
    "A3": ["background", "current_condition", "goal", "root_cause", "countermeasures", "implementation", "follow_up"],
    "PDSA": ["plan", "do", "study", "act"],
    "Kaizen": ["prepare", "execute", "sustain"],
    "Just-Do-It": ["implement", "verify"],
}

# Required artifact types before a gate can be approved
GATE_REQUIREMENTS: dict[str, list[str]] = {
    "define": ["project_charter"],
    "measure": ["data_collection_plan"],
    "analyze": [],  # At least one hypothesis test recommended, not hard-required
    "improve": ["pilot_plan"],
    "control": ["control_plan"],
}


# ---------------------------------------------------------------------------
# Phase Transition Logic
# ---------------------------------------------------------------------------

async def validate_phase_transition(
    initiative: Initiative,
    from_phase: str,
    to_phase: str,
    methodology: str,
) -> tuple[bool, str]:
    """
    Validate that a phase transition is allowed.

    Rules:
    - Can only advance to the next sequential phase
    - Previous phase must be completed
    - Cannot skip phases

    Returns:
        (is_valid, reason)
    """
    phases = METHODOLOGY_PHASES.get(methodology, METHODOLOGY_PHASES["DMAIC"])

    if from_phase not in phases:
        return False, f"Unknown phase '{from_phase}' for methodology {methodology}"
    if to_phase not in phases:
        return False, f"Unknown phase '{to_phase}' for methodology {methodology}"

    from_idx = phases.index(from_phase)
    to_idx = phases.index(to_phase)

    if to_idx != from_idx + 1:
        expected_next = phases[from_idx + 1] if from_idx + 1 < len(phases) else "complete"
        return False, f"Cannot jump from '{from_phase}' to '{to_phase}'. Next phase is '{expected_next}'"

    return True, "OK"


async def check_gate_readiness(
    initiative_id: UUID,
    phase_name: str,
    db: AsyncSession,
) -> dict:
    """
    Check whether a phase gate can be approved.
    Returns a readiness report with pass/fail per criterion.

    Returns:
        {
            "ready": bool,
            "criteria": [
                {"name": "Project charter exists", "met": True},
                ...
            ],
            "missing": ["list of unmet criteria"]
        }
    """
    # Get the phase
    result = await db.execute(
        select(Phase).where(
            Phase.initiative_id == initiative_id,
            Phase.phase_name == phase_name,
        )
    )
    phase = result.scalar_one_or_none()
    if phase is None:
        return {"ready": False, "criteria": [], "missing": [f"Phase '{phase_name}' not found"]}

    # Check required artifacts
    required = GATE_REQUIREMENTS.get(phase_name, [])
    criteria = []
    missing = []

    for artifact_type in required:
        art_result = await db.execute(
            select(PhaseArtifact).where(
                PhaseArtifact.phase_id == phase.id,
                PhaseArtifact.artifact_type == artifact_type,
            )
        )
        artifact = art_result.scalar_one_or_none()
        met = artifact is not None
        criteria.append({
            "name": f"{artifact_type.replace('_', ' ').title()} exists",
            "met": met,
            "artifact_id": str(artifact.id) if artifact else None,
        })
        if not met:
            missing.append(f"Missing required artifact: {artifact_type}")

    # Check phase has been started
    if phase.status == "not_started":
        missing.append("Phase has not been started yet")
        criteria.append({"name": "Phase started", "met": False})
    else:
        criteria.append({"name": "Phase started", "met": True})

    return {
        "ready": len(missing) == 0,
        "criteria": criteria,
        "missing": missing,
        "completeness_score": phase.completeness_score,
    }


async def advance_phase(
    initiative_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Advance an initiative to its next phase.
    Completes the current phase and starts the next one.

    Returns:
        {"previous_phase": "define", "current_phase": "measure", "status": "advanced"}
        or {"status": "completed"} if all phases are done
    """
    init_result = await db.execute(
        select(Initiative).where(Initiative.id == initiative_id)
    )
    initiative = init_result.scalar_one_or_none()
    if initiative is None:
        return {"status": "error", "detail": "Initiative not found"}

    methodology = initiative.methodology or "DMAIC"
    phases = METHODOLOGY_PHASES.get(methodology, METHODOLOGY_PHASES["DMAIC"])
    current = initiative.current_phase

    if current not in phases:
        return {"status": "error", "detail": f"Current phase '{current}' not recognized"}

    current_idx = phases.index(current)

    # Mark current phase as completed
    phase_result = await db.execute(
        select(Phase).where(
            Phase.initiative_id == initiative_id,
            Phase.phase_name == current,
        )
    )
    current_phase = phase_result.scalar_one_or_none()
    if current_phase:
        current_phase.status = "completed"
        current_phase.completed_at = datetime.now(timezone.utc)

    previous_phase = current

    # Is there a next phase?
    if current_idx + 1 < len(phases):
        next_name = phases[current_idx + 1]

        # Start next phase
        next_result = await db.execute(
            select(Phase).where(
                Phase.initiative_id == initiative_id,
                Phase.phase_name == next_name,
            )
        )
        next_phase = next_result.scalar_one_or_none()
        if next_phase:
            next_phase.status = "in_progress"
            next_phase.started_at = datetime.now(timezone.utc)

        # Update initiative
        initiative.current_phase = next_name
        initiative.updated_at = datetime.now(timezone.utc)

        # Update phase_progress
        progress = dict(initiative.phase_progress or {})
        progress[previous_phase] = 100
        initiative.phase_progress = progress

        await db.flush()
        return {"previous_phase": previous_phase, "current_phase": next_name, "status": "advanced"}
    else:
        # All phases complete
        initiative.status = "completed"
        initiative.current_phase = "complete"
        initiative.actual_completion = datetime.now(timezone.utc).date()
        initiative.updated_at = datetime.now(timezone.utc)

        await db.flush()
        return {"previous_phase": previous_phase, "current_phase": "complete", "status": "completed"}
