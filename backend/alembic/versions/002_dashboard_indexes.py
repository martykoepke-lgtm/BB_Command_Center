"""Add indexes for dashboard query performance.

Revision ID: 002
Revises: 001
Create Date: 2026-02-12

Beacon Phase 3: indexes to support dashboard aggregation queries.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Action items by due date — used by upcoming deadlines query
    op.create_index(
        "ix_action_items_due_date",
        "action_items",
        ["due_date"],
        postgresql_where="status NOT IN ('completed', 'deferred') AND due_date IS NOT NULL",
    )

    # Initiatives by actual_completion — used by trend calculations
    op.create_index(
        "ix_initiatives_actual_completion",
        "initiatives",
        ["actual_completion"],
        postgresql_where="actual_completion IS NOT NULL",
    )

    # Initiatives composite: status + current_phase — used by dashboard filters
    op.create_index(
        "ix_initiatives_status_phase",
        "initiatives",
        ["status", "current_phase"],
    )

    # Reports by initiative — used by report listing
    # (ix_reports_initiative already exists in 001, skip if present)


def downgrade() -> None:
    op.drop_index("ix_initiatives_status_phase", table_name="initiatives")
    op.drop_index("ix_initiatives_actual_completion", table_name="initiatives")
    op.drop_index("ix_action_items_due_date", table_name="action_items")
