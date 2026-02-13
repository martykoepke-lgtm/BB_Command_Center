"""
Datasets API — upload, profile, and manage datasets for statistical analysis.

Routes:
  POST   /api/initiatives/{id}/datasets  — Upload dataset (multipart)
  GET    /api/initiatives/{id}/datasets  — List datasets
  GET    /api/datasets/{id}              — Dataset detail with profile
  GET    /api/datasets/{id}/preview      — First N rows
  DELETE /api/datasets/{id}              — Delete dataset
"""

from __future__ import annotations

import io
import json
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.analysis import Dataset
from app.schemas.supporting import DatasetOut
from app.services.event_bus import DATASET_UPLOADED, get_event_bus

router = APIRouter(tags=["Datasets"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile_dataframe(df: pd.DataFrame) -> tuple[list[dict], dict, list[dict]]:
    """
    Generate column metadata, summary statistics, and data preview from a DataFrame.

    Returns:
        (columns_info, summary_stats, preview_rows)
    """
    columns_info = []
    for col in df.columns:
        info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            info["min"] = float(desc.get("min", 0))
            info["max"] = float(desc.get("max", 0))
            info["mean"] = float(desc.get("mean", 0))
            info["std"] = float(desc.get("std", 0))
        columns_info.append(info)

    # Summary stats for numeric columns
    summary = {}
    numeric_df = df.select_dtypes(include=["number"])
    if not numeric_df.empty:
        desc = numeric_df.describe().to_dict()
        # Convert numpy types to native Python for JSON serialization
        summary = json.loads(json.dumps(desc, default=str))

    # Preview: first 50 rows
    preview = json.loads(df.head(50).to_json(orient="records", date_format="iso", default_handler=str))

    return columns_info, summary, preview


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/initiatives/{initiative_id}/datasets", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    initiative_id: UUID,
    file: UploadFile = File(...),
    name: str = Form(None),
    description: str = Form(None),
    phase_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV or Excel dataset. Auto-generates a data profile
    (column types, descriptive statistics, data preview).
    """
    # Validate file type
    filename = file.filename or "unknown"
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    # Read into DataFrame
    content = await file.read()
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    # Profile the data
    columns_info, summary_stats, preview = _profile_dataframe(df)

    dataset = Dataset(
        initiative_id=initiative_id,
        phase_id=UUID(phase_id) if phase_id else None,
        name=name or filename,
        description=description,
        file_path=None,  # File storage integration comes later (Atlas agent)
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns_info,
        summary_stats=summary_stats,
        data_preview=preview,
        uploaded_by=current_user.id,
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)

    # Publish event for workflow chain (Data Agent quality assessment)
    try:
        bus = get_event_bus()
        await bus.publish(DATASET_UPLOADED, {
            "dataset_id": str(dataset.id),
            "initiative_id": str(initiative_id),
            "uploaded_by": str(current_user.id),
        })
    except RuntimeError:
        pass  # EventBus not initialized (e.g., in tests)

    return dataset


@router.get("/initiatives/{initiative_id}/datasets", response_model=list[DatasetOut])
async def list_datasets(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets for an initiative."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.initiative_id == initiative_id)
        .order_by(Dataset.created_at.desc())
    )
    return result.scalars().all()


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dataset detail including column profile and summary stats."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the first 50 rows of a dataset as JSON."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"rows": dataset.data_preview or [], "row_count": dataset.row_count, "column_count": dataset.column_count}


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dataset and its associated analyses."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset)
    await db.flush()
