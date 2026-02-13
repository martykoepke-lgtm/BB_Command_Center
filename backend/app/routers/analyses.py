"""
Statistical analysis API — run tests, get results, AI interpretation.

Routes:
  GET    /api/initiatives/{id}/analyses     — List analyses for initiative
  POST   /api/initiatives/{id}/analyses     — Create & run a statistical analysis
  GET    /api/analyses/{id}                 — Get analysis results
  POST   /api/analyses/{id}/rerun           — Rerun an existing analysis
  POST   /api/analyses/{id}/execute         — Execute (alias for rerun)
  DELETE /api/analyses/{id}                 — Delete analysis

This router is the API surface for the Sigma agent (statistical engine).
The actual test execution is delegated to app.stats.engine (Phase 2).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import Dataset, StatisticalAnalysis
from app.models.user import User
from app.schemas.analysis import AnalysisCreate, AnalysisOut, AnalysisRerun

router = APIRouter(tags=["Statistical Analyses"])


@router.get("/initiatives/{initiative_id}/analyses", response_model=list[AnalysisOut])
async def list_analyses(
    initiative_id: UUID,
    test_category: str | None = Query(None, description="Filter by category (hypothesis, descriptive, spc, etc.)"),
    status: str | None = Query(None, description="Filter by status (pending, running, completed, failed)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all statistical analyses for an initiative."""
    query = select(StatisticalAnalysis).where(
        StatisticalAnalysis.initiative_id == initiative_id
    )
    if test_category:
        query = query.where(StatisticalAnalysis.test_category == test_category)
    if status:
        query = query.where(StatisticalAnalysis.status == status)
    query = query.order_by(StatisticalAnalysis.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/analyses", response_model=AnalysisOut, status_code=201)
async def create_analysis(
    initiative_id: UUID,
    payload: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create and execute a statistical analysis.

    The test configuration specifies which test to run and its parameters.
    Execution is handled by the stats engine (app.stats.engine).
    """
    # Validate dataset exists if provided
    if payload.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == payload.dataset_id)
        )
        if ds_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Dataset not found")

    analysis = StatisticalAnalysis(
        initiative_id=initiative_id,
        dataset_id=payload.dataset_id,
        phase_id=payload.phase_id,
        test_type=payload.test_type,
        test_category=payload.test_category,
        configuration=payload.configuration,
        ai_recommended=payload.ai_recommended,
        ai_reasoning=payload.ai_reasoning,
        run_by=current_user.id,
        status="pending",
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    # Execute the test via stats engine
    try:
        from app.stats.engine import execute_analysis
        result = await execute_analysis(analysis.id, db)
        # Engine updates the analysis record directly
        await db.refresh(analysis)
    except ImportError:
        # Stats engine not yet implemented (Phase 2 — Sigma agent)
        # Mark as pending; Sigma will implement execute_analysis
        pass
    except Exception as e:
        analysis.status = "failed"
        analysis.results = {"error": str(e)}
        await db.flush()
        await db.refresh(analysis)

    return analysis


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single analysis with its results."""
    result = await db.execute(
        select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/analyses/{analysis_id}/rerun", response_model=AnalysisOut)
async def rerun_analysis(
    analysis_id: UUID,
    payload: AnalysisRerun | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rerun an existing analysis, optionally with updated configuration.
    Resets status to pending and clears previous results.
    """
    result = await db.execute(
        select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Update config if provided
    if payload and payload.configuration:
        analysis.configuration = payload.configuration

    # Reset for rerun
    analysis.status = "pending"
    analysis.results = None
    analysis.charts = None
    analysis.ai_interpretation = None
    analysis.ai_next_steps = None
    analysis.run_by = current_user.id
    analysis.run_at = None
    analysis.duration_ms = None
    await db.flush()

    # Execute
    try:
        from app.stats.engine import execute_analysis
        await execute_analysis(analysis.id, db)
        await db.refresh(analysis)
    except ImportError:
        pass
    except Exception as e:
        analysis.status = "failed"
        analysis.results = {"error": str(e)}
        await db.flush()
        await db.refresh(analysis)

    return analysis


@router.post("/analyses/{analysis_id}/execute", response_model=AnalysisOut)
async def execute_analysis_endpoint(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute (rerun) an existing analysis.
    Alias for /analyses/{id}/rerun to match frontend convention.
    """
    result = await db.execute(
        select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Reset for execution
    analysis.status = "pending"
    analysis.results = None
    analysis.charts = None
    analysis.ai_interpretation = None
    analysis.ai_next_steps = None
    analysis.run_by = current_user.id
    analysis.run_at = None
    analysis.duration_ms = None
    await db.flush()

    try:
        from app.stats.engine import execute_analysis
        await execute_analysis(analysis.id, db)
        await db.refresh(analysis)
    except ImportError:
        pass
    except Exception as e:
        analysis.status = "failed"
        analysis.results = {"error": str(e)}
        await db.flush()
        await db.refresh(analysis)

    return analysis


@router.delete("/analyses/{analysis_id}", status_code=204)
async def delete_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a statistical analysis."""
    result = await db.execute(
        select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await db.delete(analysis)
    await db.flush()
