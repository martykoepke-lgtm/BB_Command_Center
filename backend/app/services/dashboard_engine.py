"""
Dashboard Engine — aggregation and calculation logic for all dashboard views.

Provides computed metrics that go beyond simple CRUD queries:
  - Health scoring (on_track / at_risk / blocked)
  - Trend calculations (12-month rolling)
  - Upcoming deadlines with initiative context
  - Action item compliance rates
  - Phase aging (days in current phase)
  - Action burndown data

Used by routers/dashboards.py to serve the Portfolio, Team, Initiative,
and Pipeline dashboard endpoints.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, case, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.initiative import Initiative
from app.models.phase import Phase
from app.models.request import Request
from app.models.supporting import ActionItem, Metric, WorkloadEntry
from app.models.analysis import StatisticalAnalysis
from app.models.user import User, Team, team_members
from app.schemas.dashboard import (
    AnalysisSummary,
    BurndownPoint,
    DeadlineItem,
    InitiativeMetrics,
    InitiativeSummaryItem,
    MemberMetrics,
    MetricDetail,
    PhaseDetail,
    PipelineMetrics,
    PortfolioMetrics,
    RecentRequest,
    TeamMetrics,
    TrendPoint,
)


class DashboardEngine:
    """Aggregation engine for dashboard data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Portfolio Dashboard
    # ------------------------------------------------------------------

    async def get_portfolio_metrics(
        self, team_id: UUID | None = None,
    ) -> PortfolioMetrics:
        """
        Portfolio-level roll-up of all initiatives (optionally filtered by team).
        """
        base_filter = []
        if team_id:
            base_filter.append(Initiative.team_id == team_id)

        # --- Status distribution ---
        status_q = (
            select(Initiative.status, func.count(Initiative.id))
            .where(*base_filter)
            .group_by(Initiative.status)
        )
        status_result = await self.db.execute(status_q)
        status_counts = {row[0]: row[1] for row in status_result.all()}
        total = sum(status_counts.values())

        # --- Methodology distribution ---
        method_q = (
            select(Initiative.methodology, func.count(Initiative.id))
            .where(*base_filter)
            .group_by(Initiative.methodology)
        )
        method_result = await self.db.execute(method_q)
        methodology_counts = {row[0]: row[1] for row in method_result.all()}

        # --- Priority distribution ---
        priority_q = (
            select(Initiative.priority, func.count(Initiative.id))
            .where(*base_filter)
            .group_by(Initiative.priority)
        )
        priority_result = await self.db.execute(priority_q)
        priority_counts = {row[0]: row[1] for row in priority_result.all()}

        # --- Phase distribution (active only) ---
        phase_q = (
            select(Initiative.current_phase, func.count(Initiative.id))
            .where(Initiative.status == "active", *base_filter)
            .group_by(Initiative.current_phase)
        )
        phase_result = await self.db.execute(phase_q)
        phase_counts = {row[0]: row[1] for row in phase_result.all()}

        # --- Savings ---
        savings_q = select(
            func.coalesce(func.sum(Initiative.projected_savings), 0),
            func.coalesce(func.sum(Initiative.actual_savings), 0),
        ).where(*base_filter)
        savings_result = await self.db.execute(savings_q)
        projected, actual = savings_result.one()

        # This-quarter actual savings (completed initiatives)
        today = date.today()
        quarter_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
        quarter_savings_q = select(
            func.coalesce(func.sum(Initiative.actual_savings), 0),
        ).where(
            Initiative.actual_completion >= quarter_start,
            Initiative.status == "completed",
            *base_filter,
        )
        quarter_result = await self.db.execute(quarter_savings_q)
        quarter_actual = float(quarter_result.scalar_one())

        # --- Action items ---
        action_counts = await self._get_action_counts(team_id)

        # --- Utilization ---
        utilization = await self._get_portfolio_utilization(team_id)

        # --- Health summary ---
        health = await self._compute_health_summary(base_filter)

        # --- Trends (last 12 months) ---
        trends = await self._compute_trends(base_filter)

        # --- Upcoming deadlines ---
        deadlines = await self._get_upcoming_deadlines(team_id)

        return PortfolioMetrics(
            initiative_counts={
                "active": status_counts.get("active", 0),
                "on_hold": status_counts.get("on_hold", 0),
                "blocked": status_counts.get("blocked", 0),
                "completed": status_counts.get("completed", 0),
                "cancelled": status_counts.get("cancelled", 0),
                "total": total,
            },
            action_counts=action_counts,
            savings={
                "projected_total": float(projected),
                "actual_total": float(actual),
                "this_quarter_actual": quarter_actual,
            },
            utilization=utilization,
            phase_distribution=phase_counts,
            status_distribution=status_counts,
            priority_distribution=priority_counts,
            methodology_distribution=methodology_counts,
            trends=trends,
            health_summary=health,
            upcoming_deadlines=deadlines,
        )

    # ------------------------------------------------------------------
    # Team Dashboard
    # ------------------------------------------------------------------

    async def get_team_metrics(self, team_id: UUID) -> TeamMetrics:
        """Team-level dashboard with per-member breakdown."""
        # Team info
        team_result = await self.db.execute(
            select(Team).where(Team.id == team_id)
        )
        team = team_result.scalar_one_or_none()
        team_name = team.name if team else "Unknown"

        # Reuse assignment engine's utilization calculation
        from app.services.assignment_engine import get_team_utilization
        util_data = await get_team_utilization(team_id, self.db)

        # Build member metrics with initiative counts
        members: list[MemberMetrics] = []
        for m in util_data.get("members", []):
            user_id = m["user_id"]
            # Count active initiatives for this member
            init_count_result = await self.db.execute(
                select(func.count(Initiative.id))
                .where(
                    Initiative.lead_analyst_id == UUID(user_id),
                    Initiative.status == "active",
                )
            )
            active_count = init_count_result.scalar_one()

            # Get initiative list for this member
            init_list_result = await self.db.execute(
                select(
                    Initiative.id, Initiative.initiative_number,
                    Initiative.title, Initiative.status,
                )
                .where(
                    Initiative.lead_analyst_id == UUID(user_id),
                    Initiative.status == "active",
                )
            )
            member_inits = [
                {"id": str(r.id), "initiative_number": r.initiative_number, "title": r.title}
                for r in init_list_result.all()
            ]

            members.append(MemberMetrics(
                user_id=user_id,
                full_name=m["full_name"],
                capacity_hours=m["capacity_hours"],
                allocated_hours=m["allocated_hours"],
                utilization_pct=m["utilization_pct"],
                active_initiative_count=active_count,
                initiatives=member_inits,
            ))

        # Team's initiatives
        init_result = await self.db.execute(
            select(Initiative)
            .where(Initiative.team_id == team_id)
            .order_by(Initiative.created_at.desc())
        )
        initiatives = [
            InitiativeSummaryItem(
                id=str(i.id),
                initiative_number=i.initiative_number,
                title=i.title,
                status=i.status,
                current_phase=i.current_phase,
                priority=i.priority,
                methodology=i.methodology,
                lead_analyst_id=str(i.lead_analyst_id) if i.lead_analyst_id else None,
            )
            for i in init_result.scalars().all()
        ]

        # Action compliance for team initiatives
        compliance = await self._get_team_action_compliance(team_id)

        return TeamMetrics(
            team_id=str(team_id),
            team_name=team_name,
            member_count=util_data.get("member_count", 0),
            average_utilization=util_data.get("average_utilization", 0),
            members=members,
            initiatives=initiatives,
            action_compliance=compliance,
            overloaded=util_data.get("overloaded", []),
            available=util_data.get("available", []),
        )

    # ------------------------------------------------------------------
    # Initiative Dashboard
    # ------------------------------------------------------------------

    async def get_initiative_metrics(
        self, initiative_id: UUID,
    ) -> InitiativeMetrics:
        """Single initiative deep-dive dashboard data."""
        # Initiative
        init_result = await self.db.execute(
            select(Initiative).where(Initiative.id == initiative_id)
        )
        init = init_result.scalar_one()

        # Phases
        phases_result = await self.db.execute(
            select(Phase)
            .where(Phase.initiative_id == initiative_id)
            .order_by(Phase.phase_order)
        )
        phases = [
            PhaseDetail(
                phase_name=p.phase_name,
                phase_order=p.phase_order,
                status=p.status,
                gate_approved=p.gate_approved,
                completeness_score=float(p.completeness_score),
                started_at=p.started_at,
                completed_at=p.completed_at,
            )
            for p in phases_result.scalars().all()
        ]

        # Metrics with percent change
        metrics_result = await self.db.execute(
            select(Metric).where(Metric.initiative_id == initiative_id)
        )
        metrics = []
        for m in metrics_result.scalars().all():
            baseline = float(m.baseline_value) if m.baseline_value else None
            current = float(m.current_value) if m.current_value else None
            pct_change = None
            if baseline and current and baseline != 0:
                pct_change = round((current - baseline) / baseline * 100, 1)
            metrics.append(MetricDetail(
                name=m.name,
                unit=m.unit,
                baseline_value=baseline,
                target_value=float(m.target_value) if m.target_value else None,
                current_value=current,
                target_met=m.target_met,
                pct_change=pct_change,
            ))

        # Action items summary
        action_result = await self.db.execute(
            select(ActionItem.status, func.count(ActionItem.id))
            .where(ActionItem.initiative_id == initiative_id)
            .group_by(ActionItem.status)
        )
        action_summary = {row[0]: row[1] for row in action_result.all()}

        # Action burndown
        burndown = await self._compute_action_burndown(initiative_id)

        # Statistical analyses
        analyses_result = await self.db.execute(
            select(StatisticalAnalysis)
            .where(StatisticalAnalysis.initiative_id == initiative_id)
            .order_by(StatisticalAnalysis.created_at.desc())
        )
        analyses = [
            AnalysisSummary(
                id=str(a.id),
                test_type=a.test_type,
                test_category=a.test_category,
                status=a.status,
                created_at=a.created_at,
            )
            for a in analyses_result.scalars().all()
        ]

        # Health score
        health = await self._compute_initiative_health(init)

        # Days in current phase
        days_in_phase = 0
        current_phase_obj = next(
            (p for p in phases if p.phase_name == init.current_phase), None,
        )
        if current_phase_obj and current_phase_obj.started_at:
            delta = datetime.now(timezone.utc) - current_phase_obj.started_at
            days_in_phase = delta.days

        return InitiativeMetrics(
            initiative_id=str(init.id),
            initiative_number=init.initiative_number,
            title=init.title,
            methodology=init.methodology,
            status=init.status,
            current_phase=init.current_phase,
            phases=phases,
            metrics=metrics,
            action_summary=action_summary,
            action_burndown=burndown,
            analyses=analyses,
            health_score=health,
            days_in_current_phase=days_in_phase,
            financial_impact={
                "projected_savings": float(init.projected_savings) if init.projected_savings else 0,
                "actual_savings": float(init.actual_savings) if init.actual_savings else 0,
            },
        )

    # ------------------------------------------------------------------
    # Pipeline Dashboard
    # ------------------------------------------------------------------

    async def get_pipeline_metrics(self) -> PipelineMetrics:
        """Request pipeline / intake funnel."""
        # Status distribution
        status_result = await self.db.execute(
            select(Request.status, func.count(Request.id))
            .group_by(Request.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}
        total = sum(status_counts.values())

        # Urgency distribution
        urgency_result = await self.db.execute(
            select(Request.urgency, func.count(Request.id))
            .group_by(Request.urgency)
        )
        urgency_counts = {row[0]: row[1] for row in urgency_result.all()}

        # Conversion rate
        converted = status_counts.get("converted", 0)
        conversion_rate = (converted / total * 100) if total > 0 else 0

        # Average review time (days)
        avg_review_result = await self.db.execute(
            select(
                func.avg(
                    extract("epoch", Request.reviewed_at - Request.submitted_at) / 86400
                )
            ).where(Request.reviewed_at.isnot(None), Request.submitted_at.isnot(None))
        )
        avg_review_raw = avg_review_result.scalar_one()
        avg_review_days = round(float(avg_review_raw), 1) if avg_review_raw else None

        # Recent requests
        recent_result = await self.db.execute(
            select(Request)
            .order_by(Request.submitted_at.desc())
            .limit(10)
        )
        recent = [
            RecentRequest(
                id=str(r.id),
                request_number=r.request_number,
                title=r.title,
                status=r.status,
                urgency=r.urgency,
                submitted_at=r.submitted_at,
            )
            for r in recent_result.scalars().all()
        ]

        return PipelineMetrics(
            total_requests=total,
            by_status=status_counts,
            by_urgency=urgency_counts,
            conversion_rate=round(conversion_rate, 1),
            avg_review_days=avg_review_days,
            recent_requests=recent,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_action_counts(self, team_id: UUID | None) -> dict:
        """Action item aggregate counts (open, overdue, due this week, etc.)."""
        today = date.today()
        week_end = today + timedelta(days=(6 - today.weekday()))  # Sunday

        # Base query — optionally filter by team's initiatives
        base = select(ActionItem)
        if team_id:
            base = base.join(
                Initiative, Initiative.id == ActionItem.initiative_id,
            ).where(Initiative.team_id == team_id)

        # Open (not completed or deferred)
        open_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .select_from(ActionItem)
            .where(ActionItem.status.notin_(["completed", "deferred"]))
        )
        open_count = open_result.scalar_one()

        # Overdue
        overdue_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.status.notin_(["completed", "deferred"]),
                ActionItem.due_date < today,
                ActionItem.due_date.isnot(None),
            )
        )
        overdue_count = overdue_result.scalar_one()

        # Due this week
        due_week_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.status.notin_(["completed", "deferred"]),
                ActionItem.due_date >= today,
                ActionItem.due_date <= week_end,
            )
        )
        due_this_week = due_week_result.scalar_one()

        # Completed this week (Monday to now)
        week_start = today - timedelta(days=today.weekday())
        completed_week_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.status == "completed",
                ActionItem.completed_at >= datetime(
                    week_start.year, week_start.month, week_start.day,
                    tzinfo=timezone.utc,
                ),
            )
        )
        completed_this_week = completed_week_result.scalar_one()

        return {
            "open": open_count,
            "overdue": overdue_count,
            "due_this_week": due_this_week,
            "completed_this_week": completed_this_week,
        }

    async def _get_portfolio_utilization(self, team_id: UUID | None) -> dict:
        """Average utilization across analysts."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # Get analysts
        user_query = select(User).where(
            User.role.in_(["analyst", "manager"]), User.is_active == True,
        )
        if team_id:
            user_query = user_query.join(
                team_members, team_members.c.user_id == User.id,
            ).where(team_members.c.team_id == team_id)

        users_result = await self.db.execute(user_query)
        users = users_result.scalars().all()

        if not users:
            return {"team_avg_pct": 0, "overloaded_count": 0, "available_count": 0}

        total_util = 0
        overloaded = 0
        available = 0

        for user in users:
            hours_result = await self.db.execute(
                select(func.coalesce(func.sum(WorkloadEntry.hours_allocated), 0))
                .where(
                    WorkloadEntry.user_id == user.id,
                    WorkloadEntry.week_of == monday,
                )
            )
            allocated = float(hours_result.scalar_one())
            capacity = float(user.capacity_hours or 40)
            util_pct = (allocated / capacity * 100) if capacity > 0 else 0
            total_util += util_pct

            if util_pct > 90:
                overloaded += 1
            elif util_pct < 60:
                available += 1

        avg = total_util / len(users) if users else 0

        return {
            "team_avg_pct": round(avg, 1),
            "overloaded_count": overloaded,
            "available_count": available,
        }

    async def _compute_health_summary(self, base_filter: list) -> dict:
        """Classify active initiatives as on_track / at_risk / blocked."""
        result = await self.db.execute(
            select(Initiative)
            .where(Initiative.status == "active", *base_filter)
        )
        initiatives = result.scalars().all()

        on_track = 0
        at_risk = 0
        blocked = 0

        for init in initiatives:
            health = await self._compute_initiative_health(init)
            if health == "blocked":
                blocked += 1
            elif health == "at_risk":
                at_risk += 1
            else:
                on_track += 1

        return {"on_track": on_track, "at_risk": at_risk, "blocked": blocked}

    async def _compute_initiative_health(self, init: Initiative) -> str:
        """
        Determine health for a single initiative.

        Rules:
          blocked  — status == "blocked" OR has open blocker action item
          at_risk  — past target_completion, OR >3 overdue actions, OR >30 days in phase
          on_track — otherwise
        """
        if init.status == "blocked":
            return "blocked"

        if init.status != "active":
            return "on_track"

        # Check for open blocker action items
        blocker_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.initiative_id == init.id,
                ActionItem.classification == "blocker",
                ActionItem.status.notin_(["completed", "deferred"]),
            )
        )
        if blocker_result.scalar_one() > 0:
            return "blocked"

        today = date.today()

        # Past target completion date
        if init.target_completion and init.target_completion < today:
            return "at_risk"

        # More than 3 overdue action items
        overdue_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.initiative_id == init.id,
                ActionItem.status.notin_(["completed", "deferred"]),
                ActionItem.due_date < today,
                ActionItem.due_date.isnot(None),
            )
        )
        if overdue_result.scalar_one() > 3:
            return "at_risk"

        # More than 30 days in current phase
        phase_result = await self.db.execute(
            select(Phase.started_at)
            .where(
                Phase.initiative_id == init.id,
                Phase.phase_name == init.current_phase,
            )
        )
        started_at = phase_result.scalar_one_or_none()
        if started_at:
            days_in_phase = (datetime.now(timezone.utc) - started_at).days
            if days_in_phase > 30:
                return "at_risk"

        return "on_track"

    async def _compute_trends(self, base_filter: list) -> list[TrendPoint]:
        """Monthly completions and savings for the last 12 months."""
        today = date.today()
        points: list[TrendPoint] = []

        for i in range(11, -1, -1):
            # Calculate month boundaries
            month_offset = today.month - i
            year = today.year
            while month_offset <= 0:
                month_offset += 12
                year -= 1
            month = month_offset

            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            month_label = month_start.strftime("%Y-%m")

            # Completions and savings for this month
            result = await self.db.execute(
                select(
                    func.count(Initiative.id),
                    func.coalesce(func.sum(Initiative.projected_savings), 0),
                    func.coalesce(func.sum(Initiative.actual_savings), 0),
                ).where(
                    Initiative.actual_completion >= month_start,
                    Initiative.actual_completion <= month_end,
                    *base_filter,
                )
            )
            row = result.one()

            points.append(TrendPoint(
                month=month_label,
                count=row[0],
                projected_savings=float(row[1]),
                actual_savings=float(row[2]),
            ))

        return points

    async def _get_upcoming_deadlines(
        self, team_id: UUID | None, limit: int = 10,
    ) -> list[DeadlineItem]:
        """Next N action items due, with initiative context."""
        today = date.today()

        query = (
            select(ActionItem, Initiative.initiative_number, Initiative.title)
            .outerjoin(Initiative, Initiative.id == ActionItem.initiative_id)
            .where(
                ActionItem.status.notin_(["completed", "deferred"]),
                ActionItem.due_date >= today,
                ActionItem.due_date.isnot(None),
            )
            .order_by(ActionItem.due_date.asc())
            .limit(limit)
        )

        if team_id:
            query = query.where(Initiative.team_id == team_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            DeadlineItem(
                action_item_id=str(row[0].id),
                title=row[0].title,
                due_date=row[0].due_date,
                priority=row[0].priority,
                status=row[0].status,
                initiative_id=str(row[0].initiative_id) if row[0].initiative_id else None,
                initiative_number=row[1],
                initiative_title=row[2],
                owner_name=row[0].owner_name,
            )
            for row in rows
        ]

    async def _get_team_action_compliance(self, team_id: UUID) -> dict:
        """Action item on-time completion rate for a team's initiatives."""
        today = date.today()

        # Total completed with due dates (for the team's initiatives)
        completed_result = await self.db.execute(
            select(
                func.count(ActionItem.id),
                func.count(ActionItem.id).filter(
                    ActionItem.completed_at <= func.cast(
                        ActionItem.due_date, ActionItem.completed_at.type,
                    )
                ) if False else func.count(ActionItem.id),  # placeholder
            )
            .join(Initiative, Initiative.id == ActionItem.initiative_id)
            .where(
                Initiative.team_id == team_id,
                ActionItem.status == "completed",
                ActionItem.due_date.isnot(None),
            )
        )
        # Simplified: count total completed and on-time separately
        total_with_due = await self.db.execute(
            select(func.count(ActionItem.id))
            .join(Initiative, Initiative.id == ActionItem.initiative_id)
            .where(
                Initiative.team_id == team_id,
                ActionItem.status == "completed",
                ActionItem.due_date.isnot(None),
            )
        )
        total_completed = total_with_due.scalar_one()

        # Overdue (not completed, past due)
        overdue_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .join(Initiative, Initiative.id == ActionItem.initiative_id)
            .where(
                Initiative.team_id == team_id,
                ActionItem.status.notin_(["completed", "deferred"]),
                ActionItem.due_date < today,
                ActionItem.due_date.isnot(None),
            )
        )
        overdue_count = overdue_result.scalar_one()

        # On-time: completed actions where completed_at date <= due_date
        # Since completed_at is datetime and due_date is date, cast for comparison
        on_time_result = await self.db.execute(
            select(func.count(ActionItem.id))
            .join(Initiative, Initiative.id == ActionItem.initiative_id)
            .where(
                Initiative.team_id == team_id,
                ActionItem.status == "completed",
                ActionItem.due_date.isnot(None),
                ActionItem.completed_at.isnot(None),
                func.cast(ActionItem.completed_at, ActionItem.due_date.type) <= ActionItem.due_date,
            )
        )
        on_time_count = on_time_result.scalar_one()

        on_time_pct = (
            round(on_time_count / total_completed * 100, 1)
            if total_completed > 0
            else 100.0
        )

        return {
            "on_time_pct": on_time_pct,
            "on_time_count": on_time_count,
            "overdue_count": overdue_count,
            "total_completed": total_completed,
        }

    async def _compute_action_burndown(
        self, initiative_id: UUID,
    ) -> list[BurndownPoint]:
        """
        Action item burndown: open vs completed count over time.

        Computes weekly snapshots from the earliest action item to now.
        """
        # Get all action items for this initiative
        result = await self.db.execute(
            select(ActionItem)
            .where(ActionItem.initiative_id == initiative_id)
            .order_by(ActionItem.created_at.asc())
        )
        actions = result.scalars().all()

        if not actions:
            return []

        # Find date range
        earliest = min(a.created_at for a in actions).date()
        today = date.today()

        # Weekly snapshots
        points: list[BurndownPoint] = []
        current = earliest
        while current <= today:
            # At this date, how many were created and how many completed?
            created_by = sum(
                1 for a in actions if a.created_at.date() <= current
            )
            completed_by = sum(
                1 for a in actions
                if a.completed_at and a.completed_at.date() <= current
            )
            open_count = created_by - completed_by

            points.append(BurndownPoint(
                date=current.isoformat(),
                open_count=open_count,
                completed_count=completed_by,
            ))
            current += timedelta(days=7)

        # Always include today as the final point
        if points and points[-1].date != today.isoformat():
            created_total = len(actions)
            completed_total = sum(1 for a in actions if a.completed_at)
            points.append(BurndownPoint(
                date=today.isoformat(),
                open_count=created_total - completed_total,
                completed_count=completed_total,
            ))

        return points
