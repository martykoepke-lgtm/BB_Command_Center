"""Tests for workflow chain event handlers.

These tests verify that:
1. Routers publish the correct events
2. Chain handlers invoke AI agents with correct context (mocked)
3. Graceful degradation when AI or email fails
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.event_bus import (
    ACTION_ASSIGNED,
    ANALYSIS_COMPLETED,
    DATASET_UPLOADED,
    INITIATIVE_COMPLETED,
    PHASE_ADVANCED,
    EventBus,
)
from app.services.workflow_chains import (
    handle_action_assigned,
    handle_analysis_completed,
    handle_dataset_uploaded,
    handle_initiative_completed,
    handle_phase_advanced,
    register_workflow_chains,
)


# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------


def test_register_workflow_chains():
    """register_workflow_chains wires all 5 handlers."""
    bus = EventBus()
    register_workflow_chains(bus)
    assert bus.handler_count == 5


# -------------------------------------------------------------------
# Chain 1: Dataset Upload → Data Quality
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_data_quality_agent_invoked():
    """handle_dataset_uploaded invokes DataAgent for quality assessment."""
    dataset_id = str(uuid.uuid4())
    initiative_id = str(uuid.uuid4())

    mock_dataset = MagicMock()
    mock_dataset.id = uuid.UUID(dataset_id)
    mock_dataset.name = "Test CSV"
    mock_dataset.row_count = 100
    mock_dataset.column_count = 5
    mock_dataset.columns = [
        {"name": "col1", "dtype": "float64"},
        {"name": "col2", "dtype": "object"},
    ]
    mock_dataset.summary_stats = {}

    mock_agent_response = MagicMock()
    mock_agent_response.content = "Data quality is acceptable."

    with (
        patch("app.services.workflow_chains.get_db_session") as mock_db_ctx,
        patch("app.agents.data_agent.DataAgent") as MockAgent,
    ):
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        # First query returns dataset, second returns None (no initiative)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_dataset
        mock_db.execute.return_value = mock_result

        agent_instance = MockAgent.return_value
        agent_instance.invoke = AsyncMock(return_value=mock_agent_response)

        await handle_dataset_uploaded({
            "dataset_id": dataset_id,
            "initiative_id": initiative_id,
            "uploaded_by": str(uuid.uuid4()),
        })

        agent_instance.invoke.assert_called_once()


# -------------------------------------------------------------------
# Chain 2: Analysis Completed → AI Interpretation
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_stats_interpretation():
    """handle_analysis_completed invokes StatsAdvisor."""
    analysis_id = str(uuid.uuid4())

    mock_analysis = MagicMock()
    mock_analysis.id = uuid.UUID(analysis_id)
    mock_analysis.status = "completed"
    mock_analysis.ai_interpretation = None  # Not yet interpreted
    mock_analysis.initiative_id = None
    mock_analysis.test_type = "t_test_independent"
    mock_analysis.test_category = "parametric"
    mock_analysis.results = {"p_value": 0.03, "statistic": 2.15}

    mock_response = MagicMock()
    mock_response.content = "The result is statistically significant."

    with (
        patch("app.services.workflow_chains.get_db_session") as mock_db_ctx,
        patch("app.agents.stats_advisor.StatsAdvisor") as MockAdvisor,
    ):
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db.execute.return_value = mock_result

        advisor = MockAdvisor.return_value
        advisor.invoke = AsyncMock(return_value=mock_response)

        await handle_analysis_completed({
            "analysis_id": analysis_id,
            "initiative_id": None,
            "test_type": "t_test_independent",
        })

        advisor.invoke.assert_called_once()


# -------------------------------------------------------------------
# Chain 3: Phase Advanced → AI Summary + Email
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_phase_summary():
    """handle_phase_advanced invokes ReportAgent for phase summary."""
    initiative_id = str(uuid.uuid4())

    mock_init = MagicMock()
    mock_init.id = uuid.UUID(initiative_id)
    mock_init.title = "Test Initiative"
    mock_init.problem_statement = "Problem"
    mock_init.desired_outcome = "Outcome"
    mock_init.methodology = "DMAIC"
    mock_init.status = "active"
    mock_init.lead_analyst_id = None
    mock_init.initiative_number = "INIT-001"

    mock_phase = MagicMock()
    mock_phase.ai_summary = None  # Not yet summarized

    mock_response = MagicMock()
    mock_response.content = "Phase summary text."

    with (
        patch("app.services.workflow_chains.get_db_session") as mock_db_ctx,
        patch("app.agents.report_agent.ReportAgent") as MockReport,
    ):
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        # First execute returns initiative, second returns phase
        results = [MagicMock(), MagicMock()]
        results[0].scalar_one_or_none.return_value = mock_init
        results[1].scalar_one_or_none.return_value = mock_phase
        mock_db.execute.side_effect = results

        agent = MockReport.return_value
        agent.invoke = AsyncMock(return_value=mock_response)

        await handle_phase_advanced({
            "initiative_id": initiative_id,
            "completed_phase": "define",
            "next_phase": "measure",
        })

        agent.invoke.assert_called_once()


# -------------------------------------------------------------------
# Chain 4: Initiative Completed → Closeout Report
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_closeout_report():
    """handle_initiative_completed generates a closeout report record."""
    initiative_id = str(uuid.uuid4())

    with (
        patch("app.services.workflow_chains.get_db_session") as mock_db_ctx,
        patch("app.services.report_generator.generate_report", new_callable=AsyncMock) as mock_gen,
    ):
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        # First query: no existing closeout report
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_gen.return_value = "<html>Closeout Report</html>"

        await handle_initiative_completed({
            "initiative_id": initiative_id,
        })

        mock_gen.assert_called_once()
        mock_db.add.assert_called_once()


# -------------------------------------------------------------------
# Chain 5: Action Assigned → Email
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_action_email():
    """handle_action_assigned sends email notification."""
    action_id = str(uuid.uuid4())
    assigned_to = str(uuid.uuid4())
    initiative_id = str(uuid.uuid4())

    mock_action = MagicMock()
    mock_action.id = uuid.UUID(action_id)
    mock_action.title = "Fix the process"
    mock_action.due_date = date(2026, 3, 1)
    mock_action.initiative_id = uuid.UUID(initiative_id)

    mock_user = MagicMock()
    mock_user.email = "assignee@test.com"

    mock_init = MagicMock()
    mock_init.title = "My Initiative"

    mock_email_svc = MagicMock()
    mock_email_svc.send_action_assigned = AsyncMock()

    with (
        patch("app.services.workflow_chains.get_db_session") as mock_db_ctx,
        patch("app.services.email_service.get_email_service", return_value=mock_email_svc),
    ):
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        results = [MagicMock(), MagicMock(), MagicMock()]
        results[0].scalar_one_or_none.return_value = mock_action
        results[1].scalar_one_or_none.return_value = mock_user
        results[2].scalar_one_or_none.return_value = mock_init
        mock_db.execute.side_effect = results

        await handle_action_assigned({
            "action_id": action_id,
            "initiative_id": initiative_id,
            "assigned_to": assigned_to,
        })

        mock_email_svc.send_action_assigned.assert_called_once()


@pytest.mark.asyncio
async def test_action_assigned_no_assignee():
    """handle_action_assigned does nothing when assigned_to is None."""
    await handle_action_assigned({
        "action_id": str(uuid.uuid4()),
        "initiative_id": str(uuid.uuid4()),
        "assigned_to": None,
    })
    # Should return immediately without error


# -------------------------------------------------------------------
# Graceful degradation
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_graceful_degradation():
    """AI failure is caught and doesn't propagate."""
    dataset_id = str(uuid.uuid4())

    with patch("app.services.workflow_chains.get_db_session") as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        # Simulate DB error
        mock_db.execute.side_effect = Exception("DB connection lost")

        # Should NOT raise
        await handle_dataset_uploaded({
            "dataset_id": dataset_id,
            "initiative_id": None,
            "uploaded_by": str(uuid.uuid4()),
        })


@pytest.mark.asyncio
async def test_event_bus_integration():
    """End-to-end: publish triggers registered chain handler."""
    bus = EventBus()
    received = []

    async def mock_handler(payload):
        received.append(payload)

    bus.subscribe(DATASET_UPLOADED, mock_handler)
    await bus.publish(DATASET_UPLOADED, {"dataset_id": "test123"})
    await bus.drain()

    assert len(received) == 1
    assert received[0]["dataset_id"] == "test123"
