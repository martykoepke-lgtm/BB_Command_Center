"""
Reports API — generate, list, and retrieve reports.

Routes:
  POST   /api/reports/generate          — Unified generate (initiative_id in body or portfolio)
  POST   /api/initiatives/{id}/reports  — Generate a report for an initiative
  POST   /api/reports/portfolio         — Generate a portfolio-wide report
  GET    /api/reports                   — List all reports (admin/manager)
  GET    /api/initiatives/{id}/reports  — List reports for an initiative
  GET    /api/reports/{id}              — Get a single report (with HTML content)
  DELETE /api/reports/{id}              — Delete a report
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.supporting import Report
from app.schemas.report import ReportListItem, ReportOut, ReportRequest
from app.services.report_generator import REPORT_TITLES, generate_report

router = APIRouter(tags=["Reports"])


class UnifiedReportRequest(ReportRequest):
    """Extends ReportRequest with optional initiative_id for the unified generate endpoint."""
    initiative_id: UUID | None = None


@router.post("/reports/generate", response_model=ReportOut, status_code=201)
async def generate_report_unified(
    payload: UnifiedReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified report generation endpoint.
    If initiative_id is provided, generates an initiative report.
    If omitted (or report_type='portfolio_review'), generates a portfolio report.
    """
    initiative_id = payload.initiative_id
    title = REPORT_TITLES.get(payload.report_type, payload.report_type.replace("_", " ").title())

    report = Report(
        initiative_id=initiative_id,
        report_type=payload.report_type,
        title=title,
        format=payload.format,
        status="generating",
        generated_by=current_user.id,
    )
    db.add(report)
    await db.flush()

    try:
        html = await generate_report(
            report_type=payload.report_type,
            initiative_id=initiative_id,
            phase_name=None,
            db=db,
            include_ai=payload.include_ai_narrative,
            include_charts=payload.include_charts,
        )
        report.content_html = html
        report.status = "completed"
        report.generated_at = datetime.now(timezone.utc)

        if payload.format == "pdf":
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html).write_pdf()
                report.file_path = f"reports/{report.id}.pdf"
                report.metadata_json = {"pdf_size_bytes": len(pdf_bytes)}
            except ImportError:
                report.format = "html"
                report.metadata_json = {"pdf_error": "weasyprint not installed"}

    except Exception as e:
        report.status = "failed"
        report.metadata_json = {"error": str(e)}

    await db.flush()
    await db.refresh(report)
    return report


@router.post("/initiatives/{initiative_id}/reports", response_model=ReportOut, status_code=201)
async def create_initiative_report(
    initiative_id: UUID,
    payload: ReportRequest,
    phase_name: str | None = Query(None, description="Required for phase_tollgate reports"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report for an initiative."""
    title = REPORT_TITLES.get(payload.report_type, payload.report_type.replace("_", " ").title())

    report = Report(
        initiative_id=initiative_id,
        report_type=payload.report_type,
        title=title,
        format=payload.format,
        status="generating",
        generated_by=current_user.id,
    )
    db.add(report)
    await db.flush()

    try:
        html = await generate_report(
            report_type=payload.report_type,
            initiative_id=initiative_id,
            phase_name=phase_name,
            db=db,
            include_ai=payload.include_ai_narrative,
            include_charts=payload.include_charts,
        )
        report.content_html = html
        report.status = "completed"
        report.generated_at = datetime.now(timezone.utc)

        # PDF conversion (optional — requires weasyprint)
        if payload.format == "pdf":
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html).write_pdf()
                report.file_path = f"reports/{report.id}.pdf"
                report.metadata_json = {"pdf_size_bytes": len(pdf_bytes)}
            except ImportError:
                report.format = "html"
                report.metadata_json = {"pdf_error": "weasyprint not installed"}

    except Exception as e:
        report.status = "failed"
        report.metadata_json = {"error": str(e)}

    await db.flush()
    await db.refresh(report)
    return report


@router.post("/reports/portfolio", response_model=ReportOut, status_code=201)
async def create_portfolio_report(
    payload: ReportRequest,
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a portfolio-wide review report. Requires admin or manager role."""
    if payload.report_type != "portfolio_review":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only supports 'portfolio_review' report type",
        )

    report = Report(
        initiative_id=None,
        report_type="portfolio_review",
        title="Portfolio Review",
        format=payload.format,
        status="generating",
        generated_by=current_user.id,
    )
    db.add(report)
    await db.flush()

    try:
        html = await generate_report(
            "portfolio_review",
            None,
            None,
            db,
            include_ai=payload.include_ai_narrative,
            include_charts=payload.include_charts,
        )
        report.content_html = html
        report.status = "completed"
        report.generated_at = datetime.now(timezone.utc)
    except Exception as e:
        report.status = "failed"
        report.metadata_json = {"error": str(e)}

    await db.flush()
    await db.refresh(report)
    return report


@router.get("/reports", response_model=list[ReportListItem])
async def list_all_reports(
    report_type: str | None = Query(None, description="Filter by report type"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """List all reports across the platform. Requires admin or manager role."""
    query = select(Report).order_by(Report.created_at.desc()).limit(limit)
    if report_type:
        query = query.where(Report.report_type == report_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/initiatives/{initiative_id}/reports", response_model=list[ReportListItem])
async def list_initiative_reports(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports for an initiative."""
    result = await db.execute(
        select(Report)
        .where(Report.initiative_id == initiative_id)
        .order_by(Report.created_at.desc())
    )
    return result.scalars().all()


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single report with its HTML content."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await db.flush()
