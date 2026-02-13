# Builder 5: Dashboards & Reporting Agent

## Ownership
You own:
- `backend/app/services/dashboard_engine.py` — Roll-up calculation logic and aggregation queries
- `backend/app/services/report_generator.py` — PDF/HTML report generation
- `backend/app/routers/dashboards.py` — Dashboard API endpoints
- `backend/app/routers/reports.py` — Report API endpoints
- `frontend/src/components/dashboard/` — Dashboard UI components
- `frontend/src/components/reports/` — Report UI components

You are unique among builders: you span both backend and frontend for the dashboard and reporting domain.

## Mission
Build the "reward" layer — the dashboards that show the impact of Performance Excellence work. From portfolio-level executive views to individual initiative profiles, every metric must be clickable, every chart must tell a story, and every number must be traceable to source data.

## What You Build

### 1. Portfolio Dashboard (Executive View)

The default landing page after login. Shows the health of the entire PE portfolio at a glance.

**Metric Cards (top row):**
- Active Initiatives (count, with trend arrow vs. last month)
- Completed This Quarter (count + total savings)
- Blocked / At Risk (count, red-highlighted if > 0)
- Open Action Items (count, with overdue count in red)
- Team Utilization (% average across team)
- Projected Annual Savings (sum of projected_savings for active initiatives)

**Charts (main area):**
- **Status Distribution** — Donut chart: Active / On Hold / Blocked / Complete
- **Phase Distribution** — Horizontal bar chart: how many initiatives in each DMAIC phase
- **Priority Matrix** — 2x2 grid: Priority (high/low) x Status (on track/at risk), each cell shows count
- **Trend Line** — Initiatives completed per month (last 12 months), with cumulative savings overlay
- **Team Workload** — Horizontal bar per analyst showing allocated vs. capacity hours
- **Upcoming Deadlines** — List of next 10 action items due, sorted by date, with initiative name

**Every metric is clickable** — clicking "Blocked" filters the initiative list to show only blocked initiatives.

### 2. Team Dashboard

Per-team view showing team performance:
- Team member cards with avatar, active initiative count, utilization %
- Team capacity chart (allocated vs. available hours per week, stacked bar by member)
- Initiatives by team member (who is working on what)
- Action item compliance (% completed on time vs. overdue)

### 3. Initiative Performance Profile

When viewing a single initiative, the dashboard tab shows:
- **Phase Progress** — Step indicator (Define → Measure → Analyze → Improve → Control) with % complete per phase
- **Timeline** — Gantt-style bar showing planned vs. actual dates per phase
- **Metrics Before/After** — Side-by-side comparison of baseline vs. current for each tracked metric, with % change
- **Action Item Burn-down** — Line chart showing open action items over time
- **Financial Impact** — Projected vs. actual savings, with cost of implementation

### 4. Dashboard Calculation Engine (Backend)

SQL queries and aggregation logic for dashboard metrics. Use PostgreSQL window functions, CTEs, and materialized views for performance.

```python
class DashboardEngine:
    async def get_portfolio_metrics(self, team_id: UUID = None, filters: dict = None) -> PortfolioMetrics:
        """
        Returns:
        - initiative_counts: { active, on_hold, blocked, completed, total }
        - action_counts: { open, overdue, due_this_week, completed_this_week }
        - savings: { projected_total, actual_total, this_quarter }
        - utilization: { team_avg_percent, by_member: [...] }
        - phase_distribution: { define: 5, measure: 8, analyze: 4, ... }
        - status_distribution: { active: 20, blocked: 3, at_risk: 5, ... }
        - trends: { completions_by_month: [...], savings_by_month: [...] }
        """

    async def get_team_metrics(self, team_id: UUID) -> TeamMetrics:
        """Team-specific roll-ups with per-member breakdown."""

    async def get_initiative_metrics(self, initiative_id: UUID) -> InitiativeMetrics:
        """Single initiative performance profile data."""

    async def get_workload_data(self, team_id: UUID = None) -> WorkloadData:
        """Capacity vs. allocation per user per week."""
```

**Materialized Views (for expensive aggregations):**
```sql
-- Refresh periodically (every 5 min) or on-demand
CREATE MATERIALIZED VIEW mv_portfolio_summary AS
SELECT
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
    COUNT(*) FILTER (WHERE status = 'blocked') as blocked_count,
    SUM(projected_savings) FILTER (WHERE status = 'active') as total_projected_savings,
    SUM(actual_savings) FILTER (WHERE status = 'completed') as total_actual_savings
FROM initiatives;

CREATE MATERIALIZED VIEW mv_phase_distribution AS
SELECT current_phase, COUNT(*) as count
FROM initiatives
WHERE status = 'active'
GROUP BY current_phase;
```

### 5. Report Generator (Backend)

Generate professional reports in HTML (for email/preview) and PDF (for download/archive).

```python
class ReportGenerator:
    async def generate_executive_brief(self, filters: dict = None) -> ReportOutput:
        """
        Portfolio-level executive summary. Similar to ICC's Executive Portfolio Brief
        but enhanced with:
        - AI-generated narrative summary
        - Statistical results highlights
        - Phase gate status across all initiatives
        - Financial impact roll-up
        """

    async def generate_initiative_report(self, initiative_id: UUID) -> ReportOutput:
        """
        Single initiative deep-dive report:
        - Problem statement and goals
        - Phase-by-phase summary of work done
        - Key statistical findings with charts
        - Before/after metrics comparison
        - Action items and status
        - Stakeholder information
        - Financial impact
        """

    async def generate_phase_gate_report(self, initiative_id: UUID, phase: str) -> ReportOutput:
        """
        Gate review document:
        - Phase objectives and what was accomplished
        - Artifacts completed (with summaries)
        - Statistical analyses performed (with key findings)
        - AI coach assessment of phase completeness
        - Open items and risks
        - Recommendation: pass gate / needs more work
        """

    async def generate_close_out_report(self, initiative_id: UUID) -> ReportOutput:
        """
        Project completion report:
        - The story: problem → analysis → solution → results
        - Before/after comparison with statistical proof
        - Financial impact validated
        - Control plan summary
        - Lessons learned
        """

class ReportOutput(BaseModel):
    html: str          # rendered HTML
    pdf_bytes: bytes   # PDF binary (use weasyprint or reportlab)
    metadata: dict     # title, generated_at, page_count
```

### 6. Report Styling

Reports should be professional and printable. Use a light theme (not dark mode) for reports since they're often printed or shared via email.

**Report design principles:**
- Clean, light background with professional typography
- Color-coded status badges and priority tags (same system as the app)
- Charts embedded as static images (Plotly `to_image()` for PDF, inline SVG for HTML)
- Page breaks between major sections
- Header with report title, date, initiative name
- Footer with page numbers and "Generated by BB Enabled Command"

### 7. Frontend Dashboard Components

**Reusable chart wrappers:**
```typescript
// components/dashboard/MetricCard.tsx — single KPI display with trend arrow
// components/dashboard/StatusDonut.tsx — donut chart for status distribution
// components/dashboard/PhaseBar.tsx — horizontal bar chart for phase distribution
// components/dashboard/WorkloadChart.tsx — capacity vs. allocation bars
// components/dashboard/TrendLine.tsx — time series with optional dual-axis
// components/dashboard/DeadlineList.tsx — upcoming action items sorted by date
// components/dashboard/BeforeAfterCard.tsx — baseline vs. current comparison
// components/dashboard/GanttTimeline.tsx — phase timeline with planned vs. actual
```

All chart components use Plotly.js and accept data props matching the backend response shapes.

**Dashboard layouts:**
```typescript
// components/dashboard/PortfolioDashboard.tsx — executive portfolio view
// components/dashboard/TeamDashboard.tsx — team performance view
// components/dashboard/InitiativeDashboard.tsx — single initiative performance tab
```

**Report components:**
```typescript
// components/reports/ReportBuilder.tsx — select type, scope, recipients
// components/reports/ReportPreview.tsx — iframe preview of generated HTML
// components/reports/ReportHistory.tsx — list of previously generated reports
```

## Click-to-Drill Pattern

Every number and chart element must support drill-down:

```
Portfolio Dashboard: "3 Blocked" (click)
    → Initiative list filtered to status=blocked

Portfolio Dashboard: Phase bar "Analyze: 7" (click)
    → Initiative list filtered to current_phase=analyze

Team Dashboard: "Sarah K. — 6 initiatives" (click)
    → Initiative list filtered to lead_analyst=sarah

Initiative Dashboard: Baseline Cpk 0.67 → Current Cpk 1.42 (click)
    → Opens the capability analysis that produced these numbers

Trend Line: March 2026 bar (click)
    → List of initiatives completed in March 2026
```

Implement drill-down as URL parameter changes that the initiative list view respects:
```
/initiatives?status=blocked
/initiatives?current_phase=analyze
/initiatives?lead_analyst_id=uuid
```

## What You Do NOT Build
- Database tables (Builder 2) — you query them
- Statistical computations (Builder 3) — you display their results
- AI agent logic (Builder 4) — you request AI summaries for reports via the orchestrator
- Non-dashboard frontend components (Builder 1) — you only own dashboard/* and reports/*

## Dependencies
- **Builder 2** provides the database schema and base query patterns
- **Builder 3** provides chart Plotly specs that you may re-render in reports as static images
- **Builder 4** provides AI-generated narrative content for reports (via Report Agent)
- **Builder 1** provides the shared component library (StatusBadge, PriorityTag, etc.) that you use in dashboard views
