"""
Statistical analysis execution engine.

This module is the entry point for all statistical test execution.
It bridges Forge's async DB infrastructure with Sigma's scipy/statsmodels
test implementations.

Flow:
  1. Router creates a StatisticalAnalysis record with status="pending"
  2. Router calls execute_analysis(analysis_id, db)
  3. Engine loads the analysis config + dataset data
  4. Engine reconstructs a pandas DataFrame from stored data
  5. Engine dispatches to the appropriate test runner
  6. Dual-layer validation: programmatic checks + AI review
  7. Engine stores results, validation, charts, and timing back on the analysis record
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Dataset, StatisticalAnalysis
from app.stats import AnalysisResult
from app.stats.validator import run_full_validation

# Import all test modules — triggers registration
from app.stats import descriptive, comparison, regression, spc, capability, doe


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

_TEST_RUNNERS: dict[str, Callable] = {}


def register_test(test_type: str):
    """Decorator to register a statistical test implementation."""
    def decorator(func):
        _TEST_RUNNERS[test_type] = func
        return func
    return decorator


def get_available_tests() -> list[str]:
    """Return list of registered test types."""
    return list(_TEST_RUNNERS.keys())


# ---------------------------------------------------------------------------
# Dataset → DataFrame conversion
# ---------------------------------------------------------------------------

def _dataset_to_dataframe(dataset_data: dict | None) -> pd.DataFrame:
    """
    Reconstruct a pandas DataFrame from stored dataset metadata.

    Priority:
      1. file_path — read the original uploaded file (full dataset)
      2. data_preview — fallback to the stored preview rows (first 50)

    When file storage is wired up (Atlas agent), file_path will point
    to the original CSV/Excel on S3/Supabase Storage.
    """
    if dataset_data is None:
        return pd.DataFrame()

    # Try full file first
    file_path = dataset_data.get("file_path")
    if file_path:
        try:
            if file_path.lower().endswith((".xlsx", ".xls")):
                return pd.read_excel(file_path)
            else:
                return pd.read_csv(file_path)
        except Exception:
            pass  # Fall through to preview

    # Fallback: reconstruct from preview rows (JSON records)
    preview = dataset_data.get("data_preview")
    if preview and isinstance(preview, list) and len(preview) > 0:
        return pd.DataFrame(preview)

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Register all 27 test implementations
#
# Each wrapper converts the engine's (configuration, dataset) signature
# to Sigma's (df, config) signature used by the test functions.
# ---------------------------------------------------------------------------

def _make_runner(test_fn: Callable[[pd.DataFrame, dict], AnalysisResult]):
    """Create an async runner that bridges engine ↔ test function."""
    async def runner(configuration: dict, dataset: dict | None) -> AnalysisResult:
        df = _dataset_to_dataframe(dataset)
        return test_fn(df, configuration)
    return runner


# -- Descriptive -----------------------------------------------------------
_TEST_RUNNERS["descriptive_summary"] = _make_runner(descriptive.descriptive_summary)
_TEST_RUNNERS["normality_test"] = _make_runner(descriptive.normality_test)
_TEST_RUNNERS["pareto_analysis"] = _make_runner(descriptive.pareto_analysis)

# -- Comparison ------------------------------------------------------------
_TEST_RUNNERS["one_sample_t"] = _make_runner(comparison.one_sample_t)
_TEST_RUNNERS["two_sample_t"] = _make_runner(comparison.two_sample_t)
_TEST_RUNNERS["paired_t"] = _make_runner(comparison.paired_t)
_TEST_RUNNERS["one_way_anova"] = _make_runner(comparison.one_way_anova)
_TEST_RUNNERS["two_way_anova"] = _make_runner(comparison.two_way_anova)
_TEST_RUNNERS["mann_whitney"] = _make_runner(comparison.mann_whitney)
_TEST_RUNNERS["kruskal_wallis"] = _make_runner(comparison.kruskal_wallis)
_TEST_RUNNERS["chi_square_association"] = _make_runner(comparison.chi_square_association)
_TEST_RUNNERS["chi_square_goodness"] = _make_runner(comparison.chi_square_goodness)

# -- Correlation & Regression ----------------------------------------------
_TEST_RUNNERS["correlation"] = _make_runner(regression.correlation)
_TEST_RUNNERS["simple_regression"] = _make_runner(regression.simple_regression)
_TEST_RUNNERS["multiple_regression"] = _make_runner(regression.multiple_regression)
_TEST_RUNNERS["logistic_regression"] = _make_runner(regression.logistic_regression)

# -- SPC -------------------------------------------------------------------
_TEST_RUNNERS["i_mr_chart"] = _make_runner(spc.i_mr_chart)
_TEST_RUNNERS["xbar_r_chart"] = _make_runner(spc.xbar_r_chart)
_TEST_RUNNERS["p_chart"] = _make_runner(spc.p_chart)
_TEST_RUNNERS["np_chart"] = _make_runner(spc.np_chart)
_TEST_RUNNERS["c_chart"] = _make_runner(spc.c_chart)
_TEST_RUNNERS["u_chart"] = _make_runner(spc.u_chart)

# -- Capability & MSA ------------------------------------------------------
_TEST_RUNNERS["capability_normal"] = _make_runner(capability.capability_normal)
_TEST_RUNNERS["capability_nonnormal"] = _make_runner(capability.capability_nonnormal)
_TEST_RUNNERS["msa_gage_rr"] = _make_runner(capability.msa_gage_rr)

# -- DOE -------------------------------------------------------------------
_TEST_RUNNERS["full_factorial"] = _make_runner(doe.full_factorial)
_TEST_RUNNERS["fractional_factorial"] = _make_runner(doe.fractional_factorial)
_TEST_RUNNERS["doe_analysis"] = _make_runner(doe.doe_analysis)


# ---------------------------------------------------------------------------
# Main execution entry point
# ---------------------------------------------------------------------------

async def execute_analysis(analysis_id: UUID, db: AsyncSession) -> AnalysisResult:
    """
    Execute a statistical analysis.

    Loads the analysis config, retrieves dataset if needed,
    dispatches to the appropriate test runner, and stores results.
    """
    # Load the analysis record
    result = await db.execute(
        select(StatisticalAnalysis).where(StatisticalAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise ValueError(f"Analysis {analysis_id} not found")

    # Check if test type is registered
    runner = _TEST_RUNNERS.get(analysis.test_type)
    if runner is None:
        analysis.status = "failed"
        analysis.results = {
            "error": f"Test type '{analysis.test_type}' not implemented",
            "available_tests": get_available_tests(),
        }
        await db.flush()
        raise NotImplementedError(
            f"Test '{analysis.test_type}' not yet implemented. "
            f"Available: {get_available_tests()}"
        )

    # Load dataset if referenced
    dataset_data = None
    if analysis.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == analysis.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
        if dataset:
            dataset_data = {
                "columns": dataset.columns,
                "summary_stats": dataset.summary_stats,
                "data_preview": dataset.data_preview,
                "file_path": dataset.file_path,
                "row_count": dataset.row_count,
            }

    # Execute the test
    analysis.status = "running"
    analysis.run_at = datetime.now(timezone.utc)
    await db.flush()

    start = time.perf_counter()
    try:
        test_result: AnalysisResult = await runner(
            configuration=analysis.configuration,
            dataset=dataset_data,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Store results
        analysis.status = "completed" if test_result.success else "failed"
        analysis.results = test_result.summary | {"details": test_result.details}
        analysis.charts = {
            "charts": [c.model_dump() for c in test_result.charts]
        } if test_result.charts else None
        analysis.duration_ms = elapsed_ms

        if test_result.warnings:
            analysis.results["warnings"] = test_result.warnings

        # Store interpretation context for Stats Advisor AI
        if test_result.interpretation_context:
            analysis.results["interpretation_context"] = test_result.interpretation_context

        # -----------------------------------------------------------
        # Dual-layer validation
        # -----------------------------------------------------------
        try:
            # Layer 1: Programmatic validation (instant, no AI cost)
            df = _dataset_to_dataframe(dataset_data)
            programmatic_report = run_full_validation(
                test_type=analysis.test_type,
                configuration=analysis.configuration,
                dataset_summary=dataset_data,
                result=test_result,
                df=df if not df.empty else None,
            )

            validation_result: dict = {
                "overall_verdict": "validated" if programmatic_report.passed else "concern",
                "overall_confidence": programmatic_report.confidence,
                "programmatic": programmatic_report.to_dict(),
            }

            # Layer 2: AI validation review
            try:
                from app.agents.stats_validator import StatsValidatorAgent
                validator_agent = StatsValidatorAgent()
                ai_review = await validator_agent.review_analysis(
                    test_type=analysis.test_type,
                    configuration=analysis.configuration,
                    dataset_profile=dataset_data,
                    result_summary=test_result.summary,
                    result_details=test_result.details,
                    programmatic_report=programmatic_report.to_dict(),
                )
                validation_result["ai_review"] = ai_review

                # Use AI verdict as overall if programmatic passed
                if programmatic_report.passed:
                    validation_result["overall_verdict"] = ai_review.get("verdict", "validated")
                    # Map AI confidence score to confidence level
                    ai_score = ai_review.get("confidence_score", 50)
                    if ai_score >= 75:
                        validation_result["overall_confidence"] = "high"
                    elif ai_score >= 50:
                        validation_result["overall_confidence"] = "medium"
                    else:
                        validation_result["overall_confidence"] = "low"

            except Exception:
                # AI review is optional — programmatic results still valid
                validation_result["ai_review"] = {
                    "verdict": "caution",
                    "confidence_score": 50,
                    "plain_language_summary": "AI review unavailable. Programmatic validation completed.",
                    "findings": [],
                    "recommendation": "Review programmatic findings.",
                }

            analysis.results["validation"] = validation_result

        except Exception:
            # Validation should never block test results
            pass

        await db.flush()

        # Publish event for workflow chain (Stats Advisor AI interpretation)
        try:
            from app.services.event_bus import ANALYSIS_COMPLETED, get_event_bus
            bus = get_event_bus()
            await bus.publish(ANALYSIS_COMPLETED, {
                "analysis_id": str(analysis_id),
                "initiative_id": str(analysis.initiative_id) if analysis.initiative_id else None,
                "test_type": analysis.test_type,
            })
        except (RuntimeError, ImportError):
            pass  # EventBus not initialized or not available

        return test_result

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        analysis.status = "failed"
        analysis.results = {"error": str(e)}
        analysis.duration_ms = elapsed_ms
        await db.flush()
        raise
