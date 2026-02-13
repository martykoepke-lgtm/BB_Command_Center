# Builder 1: Frontend UI Agent

## Ownership
You own the entire `frontend/` directory. Every React component, route, store, hook, type, and utility function.

## Mission
Build a high-density, data-rich UI for Performance Excellence teams. This is not a consumer app — users are analysts who need information density, fast navigation, and deep drill-down capability. Think Bloomberg Terminal meets modern React.

## Tech Stack (locked — do not deviate)
- React 18 + TypeScript (strict mode)
- Vite for bundling
- Tailwind CSS for styling
- Zustand for state management
- React Router v6 for routing
- Plotly.js for all charts and visualizations
- Lucide React for icons

## What You Build

### 1. Application Shell
- **AppShell** — Sidebar + TopBar + Main Content + sliding AI Panel
- **Sidebar** — Navigation matching the route structure in CLAUDE.md. Collapsible. Active state tracking.
- **TopBar** — Context-aware: shows current view title, breadcrumbs for drill-down views, global action buttons
- **AI Panel** — Right-side sliding panel for AI agent conversations. Appears contextually (when user asks AI a question or AI has something to say). Streams responses.

### 2. Dashboard Views
- **Portfolio Dashboard** (`/dashboard`) — The executive view. Metric cards (active, blocked, overdue, completed, savings). Status distribution chart. Phase distribution chart. Team utilization. Clickable everywhere — every number drills to a filtered list.
- **Team Dashboard** (`/team/:id`) — Team member workload bars, capacity vs. allocation, initiative assignment list.
- **Individual Workload** — Per-analyst view of their active initiatives, action items, utilization.

### 3. Request Intake
- **Request Queue** (`/requests`) — Filterable table of incoming requests with status badges, urgency tags, AI triage scores.
- **Request Form** (`/requests/new`) — Multi-step form: Problem Statement → Desired Outcome → Business Impact → Requester Info. AI triage runs automatically after submission.
- **Request Detail** (`/requests/:id`) — Shows request info + AI triage assessment + Accept/Decline actions with notes.

### 4. Initiative Views
- **Initiative Board** (`/initiatives`, board mode) — Kanban columns by lifecycle phase (Define through Control + Complete). Drag-and-drop between columns. Cards show title, status badge, priority tag, lead analyst avatar, days-in-phase indicator.
- **Initiative List** (`/initiatives`, list mode) — Sortable, filterable table. Expandable rows showing latest note. Column toggles.
- **Initiative Profile** (`/initiatives/:id`) — THE core view. This is the living profile. Two-column layout: main content (tabbed: Overview, Define, Measure, Analyze, Improve, Control, Data, Reports) + right sidebar (properties, stakeholders, quick actions, AI summary).

### 5. Phase Workspaces
- **Phase Workspace** (`/initiatives/:id/:phase`) — Dedicated workspace for each DMAIC phase. Shows:
  - Phase progress indicator
  - Artifact list with completion status
  - Artifact editor (structured forms for each artifact type)
  - AI Coach panel (phase-specific coaching conversation)
  - Action items for this phase
  - Gate review button (when all artifacts are sufficient)

### 6. Data & Analysis
- **Dataset Upload** — Drag-and-drop CSV/Excel upload. Shows immediate preview (first 50 rows). Auto-generated column profiling (type, nulls, stats).
- **Analysis Workspace** (`/initiatives/:id/data/:datasetId`) — Left panel: dataset preview + column info. Center: analysis configuration (test selection, column mapping). Right: AI Stats Advisor conversation. Bottom: results panel with charts and interpretation.
- **Results Display** — Statistical output rendered in a clean, readable format. Key numbers highlighted (p-value, effect size, confidence interval). AI interpretation in plain language below. Generated charts (Plotly interactive).

### 7. AI Chat Components
- **AIChat** — Reusable chat component with message bubbles, streaming support, suggested follow-up actions as clickable chips.
- **CoachPanel** — Phase-specific variant that pre-loads phase context.
- **StatsAdvisor** — Variant that shows test recommendations as cards with "Run This Test" buttons.
- **TriageAssistant** — Variant for request intake that shows complexity score and methodology recommendation.

### 8. Global Action Items
- **ActionBoard** (`/actions`) — Three-column layout: Overdue (red), Due This Week (yellow), Open (default). Each item shows task, initiative name, owner, due date, classification badge.

### 9. Reports
- **Report Builder** (`/reports`) — Select report type, scope, recipients. Preview in iframe. Send/download.

### 10. Shared Components
- **StatusBadge** — Color-coded badge: green (on_track/complete), yellow (at_risk), red (blocked/overdue), blue (active), gray (on_hold)
- **PriorityTag** — Color-coded: red (critical), orange (high), yellow (medium), green (low)
- **PhaseIndicator** — Horizontal step indicator showing DMAIC progress (filled/active/empty)
- **DataTable** — Reusable sortable, filterable, paginated table with expandable rows
- **Modal** — Reusable modal with header, body, footer pattern
- **UserAvatar** — Initials avatar with tooltip showing full name and role

## API Integration Pattern

Use a centralized API client. Every endpoint group gets its own file in `frontend/src/api/`:

```typescript
// api/initiatives.ts
import { api } from './client';
import type { Initiative, InitiativeCreate, PaginatedResponse } from '../types';

export const initiativeApi = {
  list: (params?: ListParams) => api.get<PaginatedResponse<Initiative>>('/initiatives', { params }),
  get: (id: string) => api.get<Initiative>(`/initiatives/${id}`),
  create: (data: InitiativeCreate) => api.post<Initiative>('/initiatives', data),
  update: (id: string, data: Partial<Initiative>) => api.patch<Initiative>(`/initiatives/${id}`, data),
  delete: (id: string) => api.delete(`/initiatives/${id}`),
};
```

## State Management Pattern

Zustand stores organized by domain:

```typescript
// stores/initiativeStore.ts — initiatives, current initiative, filters
// stores/authStore.ts — user, token, role
// stores/dashboardStore.ts — portfolio metrics, cached roll-ups
// stores/aiStore.ts — active conversations, streaming state
// stores/uiStore.ts — sidebar collapsed, theme, active view
```

## Design System

### Colors (CSS variables — support dark/light mode)
```
--bg-primary: dark mode base
--bg-card: card/panel background
--bg-elevated: modal/dropdown background
--border: subtle borders
--text-primary: main text
--text-muted: secondary text
--accent: primary action color (blue)
--success: green
--warning: yellow
--danger: red
--info: teal (AI interactions)
```

### Typography
- Headings: Inter or DM Sans (same as ICC)
- Body: Inter or DM Sans
- Monospace: JetBrains Mono (metrics, IDs, timestamps, statistical output)

### Spacing
- Component padding: 16px (cards), 24px (sections), 32px (page margins)
- Gap between cards: 12px
- Dense mode for tables: 8px row padding

## What You Do NOT Build
- Backend API endpoints (Builder 2)
- Statistical computation logic (Builder 3)
- AI agent prompts or orchestration (Builder 4)
- Dashboard roll-up SQL queries (Builder 5 owns the calculation logic, you own the rendering)

## Dependencies on Other Builders
- **Builder 2** provides Pydantic schemas → you generate TypeScript types from them
- **Builder 3** provides Plotly chart JSON specs → you render them with Plotly.js
- **Builder 4** provides WebSocket message format → you handle streaming display
- **Builder 5** provides dashboard data shapes → you render the charts and metric cards
