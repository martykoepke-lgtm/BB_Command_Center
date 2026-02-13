"""Initial schema — all 17 tables for BB Enabled Command.

Revision ID: 001
Revises: None
Create Date: 2026-02-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. users
    # -----------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("full_name", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=True),
        sa.Column("role", sa.String, nullable=False, server_default="analyst"),
        sa.Column("avatar_url", sa.String, nullable=True),
        sa.Column("skills", JSONB, server_default="[]"),
        sa.Column("capacity_hours", sa.Numeric, server_default="40"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 2. teams
    # -----------------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("department", sa.String, nullable=True),
        sa.Column("organization", sa.String, nullable=True),
        sa.Column("manager_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("settings", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 3. team_members (association)
    # -----------------------------------------------------------------------
    op.create_table(
        "team_members",
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_in_team", sa.String, server_default="member"),
        sa.Column("joined_at", sa.Date, server_default=sa.text("CURRENT_DATE")),
    )

    # -----------------------------------------------------------------------
    # 4. requests
    # -----------------------------------------------------------------------
    op.create_table(
        "requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_number", sa.String, unique=True, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requester_name", sa.String, nullable=False),
        sa.Column("requester_email", sa.String, nullable=True),
        sa.Column("requester_dept", sa.String, nullable=True),
        sa.Column("problem_statement", sa.Text, nullable=True),
        sa.Column("desired_outcome", sa.Text, nullable=True),
        sa.Column("business_impact", sa.Text, nullable=True),
        sa.Column("urgency", sa.String, server_default="medium"),
        sa.Column("complexity_score", sa.Numeric, nullable=True),
        sa.Column("recommended_methodology", sa.String, nullable=True),
        sa.Column("status", sa.String, server_default="submitted"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_initiative_id", UUID(as_uuid=True), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 5. initiatives
    # -----------------------------------------------------------------------
    op.create_table(
        "initiatives",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_number", sa.String, unique=True, nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("requests.id"), nullable=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("problem_statement", sa.Text, nullable=False),
        sa.Column("desired_outcome", sa.Text, nullable=False),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column("out_of_scope", sa.Text, nullable=True),
        sa.Column("business_case", sa.Text, nullable=True),
        # Classification
        sa.Column("methodology", sa.String, nullable=False, server_default="DMAIC"),
        sa.Column("initiative_type", sa.String, nullable=True),
        sa.Column("priority", sa.String, server_default="medium"),
        sa.Column("status", sa.String, server_default="active"),
        # Assignment
        sa.Column("lead_analyst_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("sponsor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        # Dates
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("target_completion", sa.Date, nullable=True),
        sa.Column("actual_completion", sa.Date, nullable=True),
        # Current state
        sa.Column("current_phase", sa.String, server_default="define"),
        sa.Column("phase_progress", JSONB, server_default="{}"),
        # Impact tracking
        sa.Column("projected_savings", sa.Numeric, nullable=True),
        sa.Column("actual_savings", sa.Numeric, nullable=True),
        sa.Column("projected_impact", sa.Text, nullable=True),
        sa.Column("actual_impact", sa.Text, nullable=True),
        # Metadata
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("custom_fields", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 6. phases
    # -----------------------------------------------------------------------
    op.create_table(
        "phases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_name", sa.String, nullable=False),
        sa.Column("phase_order", sa.Integer, nullable=False),
        sa.Column("status", sa.String, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gate_approved", sa.Boolean, server_default=sa.text("false")),
        sa.Column("gate_approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("gate_notes", sa.Text, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("completeness_score", sa.Numeric, server_default="0"),
        sa.UniqueConstraint("initiative_id", "phase_name", name="uq_phase_per_initiative"),
    )

    # -----------------------------------------------------------------------
    # 7. phase_artifacts
    # -----------------------------------------------------------------------
    op.create_table(
        "phase_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("status", sa.String, server_default="draft"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 8. datasets
    # -----------------------------------------------------------------------
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("file_path", sa.String, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("column_count", sa.Integer, nullable=True),
        sa.Column("columns", JSONB, nullable=False),
        sa.Column("summary_stats", JSONB, nullable=True),
        sa.Column("data_preview", JSONB, nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 9. statistical_analyses
    # -----------------------------------------------------------------------
    op.create_table(
        "statistical_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=True),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        # Test configuration
        sa.Column("test_type", sa.String, nullable=False),
        sa.Column("test_category", sa.String, nullable=False),
        sa.Column("configuration", JSONB, nullable=False),
        # AI recommendation context
        sa.Column("ai_recommended", sa.Boolean, server_default=sa.text("false")),
        sa.Column("ai_reasoning", sa.Text, nullable=True),
        # Results
        sa.Column("status", sa.String, server_default="pending"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("charts", JSONB, nullable=True),
        sa.Column("ai_interpretation", sa.Text, nullable=True),
        sa.Column("ai_next_steps", sa.Text, nullable=True),
        # Metadata
        sa.Column("run_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 10. action_items
    # -----------------------------------------------------------------------
    op.create_table(
        "action_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("classification", sa.String, server_default="action_item"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("owner_name", sa.String, nullable=True),
        sa.Column("status", sa.String, server_default="not_started"),
        sa.Column("priority", sa.String, server_default="medium"),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 11. notes
    # -----------------------------------------------------------------------
    op.create_table(
        "notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note_type", sa.String, server_default="general"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 12. documents
    # -----------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("document_type", sa.String, nullable=True),
        sa.Column("file_path", sa.String, nullable=True),
        sa.Column("external_url", sa.String, nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 13. initiative_stakeholders (composite PK)
    # -----------------------------------------------------------------------
    op.create_table(
        "initiative_stakeholders",
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 14. external_stakeholders
    # -----------------------------------------------------------------------
    op.create_table(
        "external_stakeholders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=True),
        sa.Column("organization", sa.String, nullable=True),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("role", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 15. metrics
    # -----------------------------------------------------------------------
    op.create_table(
        "metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("unit", sa.String, nullable=True),
        sa.Column("baseline_value", sa.Numeric, nullable=True),
        sa.Column("baseline_date", sa.Date, nullable=True),
        sa.Column("baseline_period", sa.String, nullable=True),
        sa.Column("target_value", sa.Numeric, nullable=True),
        sa.Column("current_value", sa.Numeric, nullable=True),
        sa.Column("current_date", sa.Date, nullable=True),
        sa.Column("current_period", sa.String, nullable=True),
        sa.Column("target_met", sa.Boolean, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 16. ai_conversations
    # -----------------------------------------------------------------------
    op.create_table(
        "ai_conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("phases.id"), nullable=True),
        sa.Column("agent_type", sa.String, nullable=False),
        sa.Column("messages", JSONB, nullable=False, server_default="[]"),
        sa.Column("context_summary", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # 17. workload_entries
    # -----------------------------------------------------------------------
    op.create_table(
        "workload_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id"), nullable=True),
        sa.Column("hours_allocated", sa.Numeric, nullable=False),
        sa.Column("week_of", sa.Date, nullable=False),
        sa.Column("actual_hours", sa.Numeric, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.UniqueConstraint("user_id", "initiative_id", "week_of", name="uq_workload_per_week"),
    )

    # -----------------------------------------------------------------------
    # 18. reports
    # -----------------------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("initiative_id", UUID(as_uuid=True), sa.ForeignKey("initiatives.id"), nullable=True),
        sa.Column("report_type", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("format", sa.String, nullable=False, server_default="html"),
        sa.Column("status", sa.String, server_default="pending"),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("file_path", sa.String, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("generated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_index("ix_requests_submitted_at", "requests", ["submitted_at"])
    op.create_index("ix_initiatives_status", "initiatives", ["status"])
    op.create_index("ix_initiatives_methodology", "initiatives", ["methodology"])
    op.create_index("ix_initiatives_lead_analyst", "initiatives", ["lead_analyst_id"])
    op.create_index("ix_initiatives_team", "initiatives", ["team_id"])
    op.create_index("ix_phases_initiative", "phases", ["initiative_id"])
    op.create_index("ix_phase_artifacts_phase", "phase_artifacts", ["phase_id"])
    op.create_index("ix_datasets_initiative", "datasets", ["initiative_id"])
    op.create_index("ix_stat_analyses_initiative", "statistical_analyses", ["initiative_id"])
    op.create_index("ix_stat_analyses_dataset", "statistical_analyses", ["dataset_id"])
    op.create_index("ix_action_items_initiative", "action_items", ["initiative_id"])
    op.create_index("ix_action_items_status", "action_items", ["status"])
    op.create_index("ix_action_items_assigned", "action_items", ["assigned_to"])
    op.create_index("ix_notes_initiative", "notes", ["initiative_id"])
    op.create_index("ix_documents_initiative", "documents", ["initiative_id"])
    op.create_index("ix_metrics_initiative", "metrics", ["initiative_id"])
    op.create_index("ix_ai_conversations_initiative", "ai_conversations", ["initiative_id"])
    op.create_index("ix_workload_user_week", "workload_entries", ["user_id", "week_of"])
    op.create_index("ix_reports_initiative", "reports", ["initiative_id"])

    # -----------------------------------------------------------------------
    # updated_at trigger function (PostgreSQL)
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply auto-update triggers to tables with updated_at
    for table in ("users", "initiatives", "phase_artifacts", "metrics", "ai_conversations"):
        op.execute(f"""
            CREATE TRIGGER set_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers first
    for table in ("users", "initiatives", "phase_artifacts", "metrics", "ai_conversations"):
        op.execute(f"DROP TRIGGER IF EXISTS set_{table}_updated_at ON {table};")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse dependency order
    op.drop_table("reports")
    op.drop_table("workload_entries")
    op.drop_table("ai_conversations")
    op.drop_table("metrics")
    op.drop_table("external_stakeholders")
    op.drop_table("initiative_stakeholders")
    op.drop_table("documents")
    op.drop_table("notes")
    op.drop_table("action_items")
    op.drop_table("statistical_analyses")
    op.drop_table("datasets")
    op.drop_table("phase_artifacts")
    op.drop_table("phases")
    op.drop_table("initiatives")
    op.drop_table("requests")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("users")
