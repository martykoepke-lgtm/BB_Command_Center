"""
Workflow chain handlers — agent-triggered automation.

Nexus Phase 5: Event handlers that react to workflow events by
invoking AI agents, sending notifications, and updating records.

Each handler is an async function that takes a payload dict.
Handlers are registered with the EventBus at app startup.
All handlers gracefully degrade — AI/email failures are logged
but never block the triggering operation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.analysis import Dataset, StatisticalAnalysis
from app.models.initiative import Initiative
from app.models.phase import Phase
from app.models.supporting import ActionItem, Report
from app.models.user import User
from app.services.event_bus import (
    ACTION_ASSIGNED,
    ANALYSIS_COMPLETED,
    DATASET_UPLOADED,
    INITIATIVE_COMPLETED,
    PHASE_ADVANCED,
    EventBus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chain 1: Dataset Upload → Data Quality Assessment
# ---------------------------------------------------------------------------

async def handle_dataset_uploaded(payload: dict) -> None:
    """
    Invoke the Data Agent to assess data quality after a dataset is uploaded.

    Payload: {dataset_id, initiative_id, uploaded_by}
    Result: Stores quality assessment in dataset.summary_stats["quality"]
    """
    dataset_id = UUID(payload["dataset_id"])
    initiative_id = UUID(payload["initiative_id"]) if payload.get("initiative_id") else None

    try:
        from app.agents.data_agent import DataAgent
        from app.agents.base import AgentContext

        async with get_db_session() as db:
            # Load dataset
            result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            if dataset is None:
                logger.warning("handle_dataset_uploaded: Dataset %s not found", dataset_id)
                return

            # Build context
            context = AgentContext()
            if initiative_id:
                init_result = await db.execute(
                    select(Initiative).where(Initiative.id == initiative_id)
                )
                init = init_result.scalar_one_or_none()
                if init:
                    context.initiative_id = init.id
                    context.initiative_title = init.title
                    context.methodology = init.methodology or ""
                    context.current_phase = init.current_phase or ""

            # Build profile summary for agent
            col_summary = ", ".join(
                f"{c['name']} ({c['dtype']})" for c in (dataset.columns or [])[:20]
            )
            prompt = (
                f"Profile and assess data quality for dataset '{dataset.name}'. "
                f"{dataset.row_count} rows, {dataset.column_count} columns. "
                f"Columns: {col_summary}. "
                f"Provide a brief quality assessment with any issues found."
            )

            agent = DataAgent()
            response = await agent.invoke(prompt, context)

            # Store quality assessment
            stats = dict(dataset.summary_stats) if dataset.summary_stats else {}
            stats["quality"] = {
                "assessment": response.content[:2000],
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            }
            dataset.summary_stats = stats
            await db.commit()

            logger.info("Data quality assessment stored for dataset %s", dataset_id)

    except Exception:
        logger.exception("handle_dataset_uploaded failed for dataset %s", dataset_id)


# ---------------------------------------------------------------------------
# Chain 2: Analysis Completed → AI Interpretation
# ---------------------------------------------------------------------------

async def handle_analysis_completed(payload: dict) -> None:
    """
    Invoke the Stats Advisor to generate a plain-language interpretation.

    Payload: {analysis_id, initiative_id, test_type}
    Result: Stores interpretation in analysis.ai_interpretation
    """
    analysis_id = UUID(payload["analysis_id"])

    try:
        from app.agents.stats_advisor import StatsAdvisor
        from app.agents.base import AgentContext

        async with get_db_session() as db:
            result = await db.execute(
                select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
            )
            analysis = result.scalar_one_or_none()
            if analysis is None or analysis.status != "completed":
                return

            # Skip if already has interpretation
            if analysis.ai_interpretation:
                return

            # Build context
            context = AgentContext()
            if analysis.initiative_id:
                init_result = await db.execute(
                    select(Initiative).where(Initiative.id == analysis.initiative_id)
                )
                init = init_result.scalar_one_or_none()
                if init:
                    context.initiative_id = init.id
                    context.initiative_title = init.title
                    context.methodology = init.methodology or ""
                    context.current_phase = init.current_phase or ""

            # Build prompt from results
            summary = analysis.results or {}
            p_value = summary.get("p_value", "N/A")
            statistic = summary.get("statistic", "N/A")

            prompt = (
                f"Interpret the results of a {analysis.test_type} ({analysis.test_category}) test. "
                f"Test statistic: {statistic}, p-value: {p_value}. "
                f"Provide a plain-language interpretation and recommended next steps."
            )

            agent = StatsAdvisor()
            response = await agent.invoke(prompt, context)

            analysis.ai_interpretation = response.content[:3000]
            await db.commit()

            logger.info("AI interpretation stored for analysis %s", analysis_id)

    except Exception:
        logger.exception("handle_analysis_completed failed for analysis %s", analysis_id)


# ---------------------------------------------------------------------------
# Chain 3: Phase Advanced → AI Summary + Email
# ---------------------------------------------------------------------------

async def handle_phase_advanced(payload: dict) -> None:
    """
    Generate an AI phase summary and send email notification on phase advance.

    Payload: {initiative_id, completed_phase, next_phase}
    Result: Stores AI summary in phase.ai_summary, sends email to sponsor/lead
    """
    initiative_id = UUID(payload["initiative_id"])
    completed_phase_name = payload["completed_phase"]

    try:
        from app.agents.report_agent import ReportAgent
        from app.agents.base import AgentContext

        async with get_db_session() as db:
            # Load initiative
            init_result = await db.execute(
                select(Initiative).where(Initiative.id == initiative_id)
            )
            init = init_result.scalar_one_or_none()
            if init is None:
                return

            # Load the completed phase
            phase_result = await db.execute(
                select(Phase).where(
                    Phase.initiative_id == initiative_id,
                    Phase.phase_name == completed_phase_name,
                )
            )
            phase = phase_result.scalar_one_or_none()
            if phase is None:
                return

            # Generate AI summary only if not already set
            if not phase.ai_summary:
                context = AgentContext(
                    initiative_id=init.id,
                    initiative_title=init.title,
                    problem_statement=init.problem_statement or "",
                    desired_outcome=init.desired_outcome or "",
                    methodology=init.methodology or "",
                    current_phase=completed_phase_name,
                    initiative_status=init.status or "",
                )

                prompt = (
                    f"Generate a brief phase gate summary for the '{completed_phase_name}' phase "
                    f"of initiative '{init.title}' ({init.methodology}). "
                    f"This phase has been completed and the project is advancing."
                )

                agent = ReportAgent()
                response = await agent.invoke(prompt, context)
                phase.ai_summary = response.content[:3000]
                await db.commit()

                logger.info(
                    "Phase summary generated for %s/%s",
                    init.initiative_number, completed_phase_name,
                )

            # Send email notification
            try:
                from app.services.email_service import get_email_service
                email_svc = get_email_service()

                # Notify lead analyst
                if init.lead_analyst_id:
                    user_result = await db.execute(
                        select(User).where(User.id == init.lead_analyst_id)
                    )
                    lead = user_result.scalar_one_or_none()
                    if lead:
                        next_phase = payload.get("next_phase", "complete")
                        await email_svc.send_phase_advance(
                            recipient_email=lead.email,
                            initiative_title=init.title,
                            initiative_id=str(init.id),
                            completed_phase=completed_phase_name,
                            next_phase=next_phase,
                        )
            except Exception:
                logger.warning("Email notification failed for phase advance (non-critical)")

    except Exception:
        logger.exception("handle_phase_advanced failed for initiative %s", initiative_id)


# ---------------------------------------------------------------------------
# Chain 4: Initiative Completed → Auto-Generate Closeout Report
# ---------------------------------------------------------------------------

async def handle_initiative_completed(payload: dict) -> None:
    """
    Auto-generate a closeout report when an initiative completes.

    Payload: {initiative_id}
    Result: Creates a Report record with closeout HTML
    """
    initiative_id = UUID(payload["initiative_id"])

    try:
        from app.services.report_generator import generate_report, REPORT_TITLES

        async with get_db_session() as db:
            # Check if a closeout report already exists
            existing = await db.execute(
                select(Report).where(
                    Report.initiative_id == initiative_id,
                    Report.report_type == "initiative_closeout",
                )
            )
            if existing.scalar_one_or_none():
                logger.info("Closeout report already exists for initiative %s", initiative_id)
                return

            # Generate the report HTML
            html = await generate_report(
                "initiative_closeout",
                initiative_id,
                None,
                db,
                include_ai=True,
                include_charts=False,
            )

            # Store as Report record
            report = Report(
                initiative_id=initiative_id,
                report_type="initiative_closeout",
                title=REPORT_TITLES["initiative_closeout"],
                format="html",
                status="completed",
                content_html=html,
                generated_at=datetime.now(timezone.utc),
                metadata_json={"auto_generated": True, "trigger": "initiative_completed"},
            )
            db.add(report)
            await db.commit()

            logger.info("Auto-generated closeout report for initiative %s", initiative_id)

            # Send email notification
            try:
                from app.services.email_service import get_email_service
                email_svc = get_email_service()

                init_result = await db.execute(
                    select(Initiative).where(Initiative.id == initiative_id)
                )
                init = init_result.scalar_one_or_none()
                if init and init.lead_analyst_id:
                    user_result = await db.execute(
                        select(User).where(User.id == init.lead_analyst_id)
                    )
                    lead = user_result.scalar_one_or_none()
                    if lead:
                        await email_svc.send_initiative_completed(
                            recipient_email=lead.email,
                            initiative_title=init.title,
                            initiative_id=str(init.id),
                            actual_savings=float(init.actual_savings) if init.actual_savings else None,
                        )
            except Exception:
                logger.warning("Email notification failed for initiative completion (non-critical)")

    except Exception:
        logger.exception("handle_initiative_completed failed for initiative %s", initiative_id)


# ---------------------------------------------------------------------------
# Chain 5: Action Assigned → Email Notification
# ---------------------------------------------------------------------------

async def handle_action_assigned(payload: dict) -> None:
    """
    Send email notification when an action item is assigned.

    Payload: {action_id, initiative_id, assigned_to}
    """
    action_id = UUID(payload["action_id"])
    assigned_to = UUID(payload["assigned_to"]) if payload.get("assigned_to") else None

    if not assigned_to:
        return  # No assignee — nothing to notify

    try:
        from app.services.email_service import get_email_service
        email_svc = get_email_service()

        async with get_db_session() as db:
            # Load action item
            action_result = await db.execute(
                select(ActionItem).where(ActionItem.id == action_id)
            )
            action = action_result.scalar_one_or_none()
            if action is None:
                return

            # Load assignee
            user_result = await db.execute(
                select(User).where(User.id == assigned_to)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                return

            # Load initiative title
            initiative_title = "Unknown Initiative"
            if action.initiative_id:
                init_result = await db.execute(
                    select(Initiative).where(Initiative.id == action.initiative_id)
                )
                init = init_result.scalar_one_or_none()
                if init:
                    initiative_title = init.title

            await email_svc.send_action_assigned(
                recipient_email=user.email,
                action_title=action.title,
                due_date=action.due_date,
                initiative_title=initiative_title,
                initiative_id=str(action.initiative_id) if action.initiative_id else None,
            )

            logger.info("Action assignment notification sent to %s", user.email)

    except Exception:
        logger.exception("handle_action_assigned failed for action %s", action_id)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_workflow_chains(bus: EventBus) -> None:
    """Register all workflow chain handlers with the event bus."""
    bus.subscribe(DATASET_UPLOADED, handle_dataset_uploaded)
    bus.subscribe(ANALYSIS_COMPLETED, handle_analysis_completed)
    bus.subscribe(PHASE_ADVANCED, handle_phase_advanced)
    bus.subscribe(INITIATIVE_COMPLETED, handle_initiative_completed)
    bus.subscribe(ACTION_ASSIGNED, handle_action_assigned)
    logger.info("Workflow chains registered: 5 handlers across 5 event types")
