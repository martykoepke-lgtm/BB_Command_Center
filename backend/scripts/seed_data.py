"""
Seed data script — populates the database with demo data for development/testing.

Run: python -m scripts.seed_data
(from the backend/ directory)

Creates:
  - 6 users (admin, 2 managers, 3 analysts)
  - 2 teams
  - 5 requests (various statuses)
  - 3 initiatives (DMAIC, A3, Kaizen) with phases
  - Action items, metrics, notes per initiative
  - Workload entries
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine, Base
from app.models.user import User, Team, team_members
from app.models.request import Request
from app.models.initiative import Initiative
from app.models.phase import Phase
from app.models.supporting import ActionItem, Metric, Note, WorkloadEntry
from app.services.auth import hash_password


# ---------------------------------------------------------------------------
# Deterministic UUIDs for cross-referencing
# ---------------------------------------------------------------------------

def _uuid(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


# Users
ADMIN_ID = _uuid(1)
MGR1_ID = _uuid(2)
MGR2_ID = _uuid(3)
ANALYST1_ID = _uuid(4)
ANALYST2_ID = _uuid(5)
ANALYST3_ID = _uuid(6)

# Teams
TEAM_OPS_ID = _uuid(10)
TEAM_QUALITY_ID = _uuid(11)

# Requests
REQ1_ID = _uuid(20)
REQ2_ID = _uuid(21)
REQ3_ID = _uuid(22)
REQ4_ID = _uuid(23)
REQ5_ID = _uuid(24)

# Initiatives
INI1_ID = _uuid(30)
INI2_ID = _uuid(31)
INI3_ID = _uuid(32)


async def seed(db: AsyncSession):
    """Insert all seed data."""

    # -------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------
    users = [
        User(
            id=ADMIN_ID,
            email="admin@bbcommand.dev",
            password_hash=hash_password("admin123"),
            full_name="Sarah Chen",
            title="Director of Performance Excellence",
            role="admin",
            skills=["lean", "six_sigma", "change_management", "strategy"],
            capacity_hours=40,
        ),
        User(
            id=MGR1_ID,
            email="mgr.ops@bbcommand.dev",
            password_hash=hash_password("manager123"),
            full_name="Marcus Johnson",
            title="Operations Manager",
            role="manager",
            skills=["process_improvement", "data_analysis", "project_management"],
            capacity_hours=40,
        ),
        User(
            id=MGR2_ID,
            email="mgr.quality@bbcommand.dev",
            password_hash=hash_password("manager123"),
            full_name="Lisa Park",
            title="Quality Manager",
            role="manager",
            skills=["spc", "audit", "iso_9001", "root_cause_analysis"],
            capacity_hours=40,
        ),
        User(
            id=ANALYST1_ID,
            email="analyst1@bbcommand.dev",
            password_hash=hash_password("analyst123"),
            full_name="James Rivera",
            title="Senior Analyst",
            role="analyst",
            skills=["six_sigma", "minitab", "data_analysis", "spc", "doe"],
            capacity_hours=40,
        ),
        User(
            id=ANALYST2_ID,
            email="analyst2@bbcommand.dev",
            password_hash=hash_password("analyst123"),
            full_name="Priya Sharma",
            title="Process Analyst",
            role="analyst",
            skills=["lean", "value_stream_mapping", "kaizen", "5s"],
            capacity_hours=40,
        ),
        User(
            id=ANALYST3_ID,
            email="analyst3@bbcommand.dev",
            password_hash=hash_password("analyst123"),
            full_name="David Kim",
            title="Data Analyst",
            role="analyst",
            skills=["data_analysis", "python", "statistics", "visualization"],
            capacity_hours=32,  # Part-time
        ),
    ]
    for u in users:
        db.add(u)
    await db.flush()

    # -------------------------------------------------------------------
    # Teams
    # -------------------------------------------------------------------
    team_ops = Team(
        id=TEAM_OPS_ID,
        name="Operations Excellence",
        description="Cross-functional operations improvement team",
        department="Operations",
        organization="BB Enterprises",
        manager_id=MGR1_ID,
    )
    team_quality = Team(
        id=TEAM_QUALITY_ID,
        name="Quality Assurance",
        description="Quality systems and statistical process control",
        department="Quality",
        organization="BB Enterprises",
        manager_id=MGR2_ID,
    )
    db.add(team_ops)
    db.add(team_quality)
    await db.flush()

    # Team memberships
    from sqlalchemy import insert
    await db.execute(insert(team_members).values([
        {"team_id": TEAM_OPS_ID, "user_id": MGR1_ID, "role_in_team": "lead"},
        {"team_id": TEAM_OPS_ID, "user_id": ANALYST1_ID, "role_in_team": "analyst"},
        {"team_id": TEAM_OPS_ID, "user_id": ANALYST2_ID, "role_in_team": "analyst"},
        {"team_id": TEAM_QUALITY_ID, "user_id": MGR2_ID, "role_in_team": "lead"},
        {"team_id": TEAM_QUALITY_ID, "user_id": ANALYST1_ID, "role_in_team": "analyst"},
        {"team_id": TEAM_QUALITY_ID, "user_id": ANALYST3_ID, "role_in_team": "analyst"},
    ]))
    await db.flush()

    # -------------------------------------------------------------------
    # Requests
    # -------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    requests = [
        Request(
            id=REQ1_ID,
            request_number="REQ-0001",
            title="Reduce lab turnaround time",
            description="Lab results consistently take 72+ hours",
            requester_name="Dr. Amanda Foster",
            requester_email="afoster@hospital.org",
            requester_dept="Pathology",
            problem_statement="Average lab turnaround time is 72 hours, causing treatment delays and patient dissatisfaction.",
            desired_outcome="Reduce average turnaround to under 48 hours for 90% of standard tests.",
            business_impact="Patient satisfaction scores dropped 15% last quarter; 3 near-miss incidents linked to delayed results.",
            urgency="high",
            status="converted",
            complexity_score=7.5,
            recommended_methodology="DMAIC",
            submitted_at=now - timedelta(days=30),
            reviewed_at=now - timedelta(days=28),
            converted_initiative_id=INI1_ID,
        ),
        Request(
            id=REQ2_ID,
            request_number="REQ-0002",
            title="Streamline patient discharge process",
            description="Discharge takes 3+ hours from physician order to patient leaving",
            requester_name="Nurse Manager Karen White",
            requester_dept="Nursing",
            problem_statement="Discharge process averages 3.2 hours from order to exit.",
            desired_outcome="Reduce to under 90 minutes with standardized workflow.",
            business_impact="Bed availability affects ED boarding times.",
            urgency="high",
            status="accepted",
            complexity_score=6.0,
            recommended_methodology="A3",
            submitted_at=now - timedelta(days=14),
            reviewed_at=now - timedelta(days=12),
        ),
        Request(
            id=REQ3_ID,
            request_number="REQ-0003",
            title="Reduce medication dispensing errors",
            description="Pharmacy reports increasing dispensing error rate",
            requester_name="PharmD Robert Lee",
            requester_dept="Pharmacy",
            problem_statement="Dispensing error rate increased from 0.3% to 0.8% over 6 months.",
            desired_outcome="Return to <0.3% error rate with sustainable controls.",
            urgency="critical",
            status="under_review",
            submitted_at=now - timedelta(days=7),
        ),
        Request(
            id=REQ4_ID,
            request_number="REQ-0004",
            title="Optimize OR scheduling utilization",
            description="OR utilization averages only 68%, well below benchmark",
            requester_name="Dr. Michael Torres",
            requester_dept="Surgery",
            urgency="medium",
            status="submitted",
            submitted_at=now - timedelta(days=3),
        ),
        Request(
            id=REQ5_ID,
            request_number="REQ-0005",
            title="Reduce supply chain waste in central sterile",
            description="High waste rate in sterile processing supplies",
            requester_name="Chris Martinez",
            requester_dept="Materials Management",
            urgency="low",
            status="submitted",
            submitted_at=now - timedelta(days=1),
        ),
    ]
    for r in requests:
        db.add(r)
    await db.flush()

    # -------------------------------------------------------------------
    # Initiatives + Phases
    # -------------------------------------------------------------------

    # Initiative 1: DMAIC — Lab Turnaround (in Measure phase)
    ini1 = Initiative(
        id=INI1_ID,
        initiative_number="INI-0001",
        request_id=REQ1_ID,
        title="Reduce Lab Turnaround Time",
        problem_statement="Average lab turnaround time is 72 hours, causing treatment delays.",
        desired_outcome="Reduce average turnaround to under 48 hours for 90% of standard tests.",
        scope="Pathology department standard blood panels and urinalysis",
        methodology="DMAIC",
        priority="high",
        status="active",
        current_phase="measure",
        lead_analyst_id=ANALYST1_ID,
        team_id=TEAM_QUALITY_ID,
        sponsor_id=ADMIN_ID,
        start_date=date.today() - timedelta(days=25),
        target_completion=date.today() + timedelta(days=65),
        projected_savings=150000,
        tags=["lab", "turnaround", "patient_satisfaction"],
    )
    db.add(ini1)
    await db.flush()

    dmaic_phases = ["define", "measure", "analyze", "improve", "control"]
    for order, name in enumerate(dmaic_phases, 1):
        phase = Phase(
            initiative_id=INI1_ID,
            phase_name=name,
            phase_order=order,
            status="completed" if name == "define" else ("in_progress" if name == "measure" else "not_started"),
            started_at=now - timedelta(days=25) if name == "define" else (now - timedelta(days=10) if name == "measure" else None),
            completed_at=now - timedelta(days=10) if name == "define" else None,
            gate_approved=name == "define",
            completeness_score=100 if name == "define" else (45 if name == "measure" else 0),
        )
        db.add(phase)

    # Initiative 2: A3 — Discharge Process (in Define phase)
    ini2 = Initiative(
        id=INI2_ID,
        initiative_number="INI-0002",
        title="Streamline Patient Discharge",
        problem_statement="Discharge process averages 3.2 hours from order to exit.",
        desired_outcome="Reduce to under 90 minutes with standardized workflow.",
        methodology="A3",
        priority="high",
        status="active",
        current_phase="background",
        lead_analyst_id=ANALYST2_ID,
        team_id=TEAM_OPS_ID,
        sponsor_id=MGR1_ID,
        start_date=date.today() - timedelta(days=5),
        target_completion=date.today() + timedelta(days=25),
        tags=["discharge", "nursing", "patient_flow"],
    )
    db.add(ini2)
    await db.flush()

    a3_phases = ["background", "current_condition", "goal", "root_cause", "countermeasures", "implementation", "follow_up"]
    for order, name in enumerate(a3_phases, 1):
        phase = Phase(
            initiative_id=INI2_ID,
            phase_name=name,
            phase_order=order,
            status="in_progress" if name == "background" else "not_started",
            started_at=now - timedelta(days=5) if name == "background" else None,
        )
        db.add(phase)

    # Initiative 3: Kaizen — 5S in Central Sterile (completed)
    ini3 = Initiative(
        id=INI3_ID,
        initiative_number="INI-0003",
        title="5S Implementation in Central Sterile",
        problem_statement="Central sterile processing area is disorganized, leading to time waste searching for supplies.",
        desired_outcome="Fully organized workspace with visual management standards.",
        methodology="Kaizen",
        priority="medium",
        status="completed",
        current_phase="complete",
        lead_analyst_id=ANALYST2_ID,
        team_id=TEAM_OPS_ID,
        sponsor_id=MGR1_ID,
        start_date=date.today() - timedelta(days=60),
        target_completion=date.today() - timedelta(days=45),
        actual_completion=date.today() - timedelta(days=42),
        projected_savings=25000,
        actual_savings=31000,
        actual_impact="Reduced search time by 70%, improved compliance scores from 65% to 94%.",
        tags=["5s", "kaizen", "sterile_processing"],
    )
    db.add(ini3)
    await db.flush()

    kaizen_phases = ["prepare", "execute", "sustain"]
    for order, name in enumerate(kaizen_phases, 1):
        phase = Phase(
            initiative_id=INI3_ID,
            phase_name=name,
            phase_order=order,
            status="completed",
            started_at=now - timedelta(days=60 - (order - 1) * 6),
            completed_at=now - timedelta(days=60 - order * 6),
            gate_approved=True,
            completeness_score=100,
        )
        db.add(phase)
    await db.flush()

    # -------------------------------------------------------------------
    # Action Items
    # -------------------------------------------------------------------
    actions = [
        ActionItem(initiative_id=INI1_ID, title="Collect 30-day baseline TAT data", status="completed", priority="high", completed_at=now - timedelta(days=15)),
        ActionItem(initiative_id=INI1_ID, title="Map current lab workflow (SIPOC)", status="completed", priority="high", completed_at=now - timedelta(days=12)),
        ActionItem(initiative_id=INI1_ID, title="Install data collection checkpoints", status="in_progress", priority="high", due_date=date.today() + timedelta(days=3)),
        ActionItem(initiative_id=INI1_ID, title="Conduct MSA on timing measurements", status="not_started", priority="medium", due_date=date.today() + timedelta(days=10)),
        ActionItem(initiative_id=INI2_ID, title="Interview nursing staff on discharge pain points", status="in_progress", priority="high", due_date=date.today() + timedelta(days=5)),
        ActionItem(initiative_id=INI2_ID, title="Document current state discharge workflow", status="not_started", priority="medium"),
    ]
    for a in actions:
        db.add(a)

    # -------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------
    metrics = [
        Metric(initiative_id=INI1_ID, name="Average Turnaround Time", unit="hours", baseline_value=72, target_value=48, current_value=65),
        Metric(initiative_id=INI1_ID, name="% Tests Under 48 Hours", unit="%", baseline_value=35, target_value=90, current_value=42),
        Metric(initiative_id=INI1_ID, name="Patient Satisfaction (Lab)", unit="score", baseline_value=3.2, target_value=4.5),
        Metric(initiative_id=INI3_ID, name="5S Audit Score", unit="%", baseline_value=65, target_value=90, current_value=94, target_met=True),
        Metric(initiative_id=INI3_ID, name="Average Search Time", unit="minutes", baseline_value=8.5, target_value=3.0, current_value=2.5, target_met=True),
    ]
    for m in metrics:
        db.add(m)

    # -------------------------------------------------------------------
    # Notes
    # -------------------------------------------------------------------
    notes = [
        Note(initiative_id=INI1_ID, author_id=ANALYST1_ID, note_type="observation", content="Noticed significant bottleneck at specimen accessioning step — manual label printing takes 3-4 minutes per batch."),
        Note(initiative_id=INI1_ID, author_id=MGR2_ID, note_type="decision", content="Approved purchase of barcode scanner system for Phase Improve — budget allocated from Q2 capital."),
        Note(initiative_id=INI2_ID, author_id=ANALYST2_ID, note_type="general", content="Initial gemba walk completed. Three main delay points identified: pharmacy clearance, transport, and discharge instructions."),
    ]
    for n in notes:
        db.add(n)

    # -------------------------------------------------------------------
    # Workload Entries
    # -------------------------------------------------------------------
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    workloads = [
        WorkloadEntry(user_id=ANALYST1_ID, initiative_id=INI1_ID, hours_allocated=20, week_of=monday),
        WorkloadEntry(user_id=ANALYST1_ID, hours_allocated=8, week_of=monday, notes="Quality audit support"),
        WorkloadEntry(user_id=ANALYST2_ID, initiative_id=INI2_ID, hours_allocated=16, week_of=monday),
        WorkloadEntry(user_id=ANALYST2_ID, hours_allocated=12, week_of=monday, notes="Kaizen event prep"),
        WorkloadEntry(user_id=ANALYST3_ID, hours_allocated=16, week_of=monday, notes="Data analysis requests"),
    ]
    for w in workloads:
        db.add(w)

    await db.flush()
    await db.commit()
    print("Seed data inserted successfully!")
    print(f"  Users: 6")
    print(f"  Teams: 2")
    print(f"  Requests: 5")
    print(f"  Initiatives: 3 (DMAIC, A3, Kaizen)")
    print(f"  Action items: {len(actions)}")
    print(f"  Metrics: {len(metrics)}")
    print(f"  Notes: {len(notes)}")
    print(f"  Workload entries: {len(workloads)}")
    print()
    print("Login credentials:")
    print("  admin@bbcommand.dev / admin123")
    print("  mgr.ops@bbcommand.dev / manager123")
    print("  analyst1@bbcommand.dev / analyst123")


async def main():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        result = await db.execute(select(func.count(User.id)))
        count = result.scalar_one()
        if count > 0:
            print(f"Database already has {count} users. Skipping seed.")
            print("To re-seed, drop and recreate the database first.")
            return

        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
