"""Add indexes for Nexus workflow chain queries.

Revision ID: 003
Revises: 002
Create Date: 2026-02-12

Nexus Phase 5: indexes to support event-driven workflow chains
(dataset lookups by initiative, action item notification queries).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Datasets by initiative — used by workflow chain dataset lookups
    op.create_index(
        "ix_datasets_initiative_id",
        "datasets",
        ["initiative_id"],
        postgresql_where="initiative_id IS NOT NULL",
    )

    # Action items by assigned_to — used by email notification lookups
    op.create_index(
        "ix_action_items_assigned_to",
        "action_items",
        ["assigned_to"],
        postgresql_where="assigned_to IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("ix_action_items_assigned_to", table_name="action_items")
    op.drop_index("ix_datasets_initiative_id", table_name="datasets")
