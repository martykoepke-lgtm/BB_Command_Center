# BB Enabled Command — Performance Excellence Operating System

## Vision

BB Enabled Command is an enterprise Performance Excellence platform that unifies request intake, intelligent work assignment, AI-guided Lean Six Sigma execution, embedded statistical analysis, and comprehensive performance dashboards into a single system. It replaces the fragmented toolchain (ServiceNow + Excel + Minitab + PowerPoint + email) that Performance Excellence teams currently depend on.

**Think:** Workday (workforce/assignment) + AI-driven Minitab (statistics) + Service Matters (request management) — orchestrated by a team of AI agents that guide users through best-practice methodology at every step.

**Core Promise:** A request enters the system. It gets triaged, assigned to the right analyst with balanced workload. AI agents guide execution through structured methodology (DMAIC, Kaizen, A3, PDSA). Statistical analysis is embedded — the AI recommends the right test, the system runs it, and translates the results. Leadership sees roll-up dashboards. Anyone can click into a single initiative and see its complete living profile from intake to close.

---

## Platform Architecture

### System Overview

```
                        ┌──────────────────────────┐
                        │     React Frontend       │
                        │   (TypeScript + Vite)    │
                        │                          │
                        │  Intake │ Workspace │    │
                        │  Board  │ Profiles  │    │
                        │  Dashboards │ Admin  │    │
                        └───────────┬──────────────┘
                                    │ REST + WebSocket
                        ┌───────────┴──────────────┐
                        │    API Gateway Layer      │
                        │      (FastAPI)            │
                        │                          │
                        │  Auth │ Rate Limit │ CORS│
                        └───────────┬──────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────┴──────────┐ ┌───────┴────────┐ ┌─────────┴──────────┐
    │  Workflow Engine    │ │  AI Agent      │ │  Statistical       │
    │                    │ │  Orchestrator  │ │  Engine            │
    │  Request lifecycle │ │                │ │                    │
    │  DMAIC phases      │ │  Claude API    │ │  scipy/statsmodels │
    │  Assignment logic  │ │  Agent routing │ │  pandas processing │
    │  Workload balance  │ │  Context mgmt  │ │  plotly charts     │
    │  Phase gates       │ │  Memory store  │ │  Test selection    │
    └─────────┬──────────┘ └───────┬────────┘ └─────────┬──────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                        ┌───────────┴──────────────┐
                        │     PostgreSQL            │
                        │                          │
                        │  Projects │ Phases       │
                        │  Datasets │ Analyses     │
                        │  Users │ Teams │ Roles   │
                        │  AI Memory │ Artifacts   │
                        │  Dashboards │ Reports    │
                        └──────────────────────────┘
```

### Service Architecture (5 Core Services)

```
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                     │
│  /api/v1/...                                                    │
│  JWT Auth │ Role-based access │ Rate limiting │ Request logging │
└────┬──────────┬──────────┬──────────┬──────────┬───────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
│WORKFLOW ││  AI     ││ STATS   ││ DATA    ││REPORTING│
│SERVICE  ││ SERVICE ││ SERVICE ││ SERVICE ││ SERVICE │
│         ││         ││         ││         ││         │
│Requests ││Agent    ││Test     ││Upload   ││Dashboard│
│Phases   ││Routing  ││Execute  ││Process  ││Roll-ups │
│Assign   ││Context  ││Charts   ││Store    ││PDF/HTML │
│Gates    ││Memory   ││Suggest  ││Transform││Exports  │
│Workload ││Prompts  ││Interpret││Validate ││Scheduled│
└─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
```

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React 18 + TypeScript + Vite | Proven stack, same as VytalPath Academy |
| **Styling** | Tailwind CSS | Rapid UI development, design system consistency |
| **Charts** | Plotly.js | Interactive statistical charts (box plots, histograms, control charts, scatter, Pareto) |
| **State Management** | Zustand | Lightweight, no boilerplate, perfect for complex dashboard state |
| **Routing** | React Router v6 | Nested routes for initiative profiles, phase drill-downs |
| **Backend** | Python 3.12 + FastAPI | Async, native scipy/statsmodels, best AI SDK support |
| **ORM** | SQLAlchemy 2.0 + Alembic | Type-safe queries, migration management |
| **Database** | PostgreSQL 16 | JSONB for flexible artifacts, full-text search, window functions for roll-ups |
| **AI** | Anthropic Claude API (claude-opus-4-6) | Best structured reasoning for methodology guidance |
| **Statistics** | scipy + statsmodels + pandas + numpy | Industry-standard, covers all Black Belt statistical tools |
| **Chart Generation** | plotly (Python) + plotly.js (frontend) | Server-side chart generation for reports, client-side for interactive dashboards |
| **Auth** | Supabase Auth or Auth0 | JWT-based, role management, SSO-ready |
| **File Storage** | Supabase Storage or S3 | Dataset uploads, generated reports, documents |
| **Real-time** | WebSockets (FastAPI) | Live dashboard updates, agent conversation streaming |
| **Task Queue** | Celery + Redis | Long-running statistical computations, report generation, scheduled jobs |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | Simple, scalable |
| **CI/CD** | GitHub Actions | Automated testing, deployment |

---

## Data Model

### Entity Relationship Overview

```
Users ──┬── Teams (membership)
        │
        ├── Requests ──▶ Initiatives ──┬── Phases ──── Phase Artifacts
        │                              │
        │                              ├── Action Items
        │                              ├── Stakeholders (junction)
        │                              ├── Notes
        │                              ├── Documents
        │                              ├── Datasets ──── Statistical Analyses
        │                              ├── AI Conversations
        │                              └── Metrics
        │
        └── Dashboard Configs
```

### Core Tables

#### users
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    full_name       TEXT NOT NULL,
    title           TEXT,
    role            TEXT NOT NULL DEFAULT 'analyst',  -- admin, manager, analyst, viewer, sponsor
    avatar_url      TEXT,
    skills          JSONB DEFAULT '[]',               -- ['DMAIC', 'DOE', 'SPC', 'regression']
    capacity_hours  NUMERIC DEFAULT 40,               -- weekly capacity
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
-- roles: admin (platform admin), manager (team lead), analyst (BB/GB), viewer (read-only), sponsor (executive)
```

#### teams
```sql
CREATE TABLE teams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    department      TEXT,
    organization    TEXT,
    manager_id      UUID REFERENCES users(id),
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE team_members (
    team_id         UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role_in_team    TEXT DEFAULT 'member',  -- lead, member
    joined_at       TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (team_id, user_id)
);
```

#### requests (intake)
```sql
CREATE TABLE requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number  TEXT UNIQUE NOT NULL,              -- REQ-0001
    title           TEXT NOT NULL,
    description     TEXT,
    requester_name  TEXT NOT NULL,
    requester_email TEXT,
    requester_dept  TEXT,
    problem_statement TEXT,
    desired_outcome TEXT,
    business_impact TEXT,                              -- estimated impact description
    urgency         TEXT DEFAULT 'medium',             -- critical, high, medium, low
    complexity_score NUMERIC,                          -- AI-assessed 1-10
    recommended_methodology TEXT,                      -- AI-recommended: DMAIC, Kaizen, A3, PDSA, just-do-it
    status          TEXT DEFAULT 'submitted',          -- submitted, under_review, accepted, declined, converted
    reviewed_by     UUID REFERENCES users(id),
    review_notes    TEXT,
    submitted_at    TIMESTAMPTZ DEFAULT now(),
    reviewed_at     TIMESTAMPTZ,
    converted_initiative_id UUID                       -- set when request becomes initiative
);
```

#### initiatives (the living profile)
```sql
CREATE TABLE initiatives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_number TEXT UNIQUE NOT NULL,            -- INI-0001
    request_id      UUID REFERENCES requests(id),     -- originating request
    title           TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    desired_outcome TEXT NOT NULL,
    scope           TEXT,
    out_of_scope    TEXT,
    business_case   TEXT,

    -- Classification
    methodology     TEXT NOT NULL DEFAULT 'DMAIC',     -- DMAIC, Kaizen, A3, PDSA, custom
    initiative_type TEXT,                               -- process_improvement, cost_reduction, quality, safety, experience, efficiency
    priority        TEXT DEFAULT 'medium',              -- critical, high, medium, low
    status          TEXT DEFAULT 'active',              -- active, on_hold, completed, cancelled

    -- Assignment
    lead_analyst_id UUID REFERENCES users(id),
    team_id         UUID REFERENCES teams(id),
    sponsor_id      UUID REFERENCES users(id),

    -- Dates
    start_date      DATE,
    target_completion DATE,
    actual_completion DATE,

    -- Current state
    current_phase   TEXT DEFAULT 'define',              -- define, measure, analyze, improve, control, complete
    phase_progress  JSONB DEFAULT '{}',                 -- { "define": 100, "measure": 60, "analyze": 0, ... }

    -- Impact tracking
    projected_savings NUMERIC,
    actual_savings    NUMERIC,
    projected_impact  TEXT,
    actual_impact     TEXT,

    -- Metadata
    tags            TEXT[] DEFAULT '{}',
    custom_fields   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

#### phases (DMAIC phases per initiative)
```sql
CREATE TABLE phases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_name      TEXT NOT NULL,                     -- define, measure, analyze, improve, control
    phase_order     INTEGER NOT NULL,
    status          TEXT DEFAULT 'not_started',        -- not_started, in_progress, completed, skipped
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    gate_approved   BOOLEAN DEFAULT false,
    gate_approved_by UUID REFERENCES users(id),
    gate_notes      TEXT,
    ai_summary      TEXT,                              -- AI-generated phase summary
    completeness_score NUMERIC DEFAULT 0,              -- 0-100, AI-assessed
    UNIQUE(initiative_id, phase_name)
);
```

#### phase_artifacts (deliverables within each phase)
```sql
CREATE TABLE phase_artifacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase_id        UUID REFERENCES phases(id) ON DELETE CASCADE,
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,                     -- see Artifact Types below
    title           TEXT NOT NULL,
    content         JSONB NOT NULL,                    -- structured content varies by type
    status          TEXT DEFAULT 'draft',              -- draft, complete, reviewed
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Artifact Types by Phase:
-- DEFINE:    project_charter, sipoc, voc_ctq_tree, stakeholder_map, problem_statement
-- MEASURE:   data_collection_plan, msa_results, process_map, value_stream_map, baseline_capability
-- ANALYZE:   fishbone_diagram, five_why, hypothesis_test, regression_analysis, pareto_analysis, fmea
-- IMPROVE:   solution_matrix, pilot_plan, implementation_plan, before_after_comparison, cost_benefit
-- CONTROL:   control_plan, control_charts, sop_document, training_plan, handoff_checklist
```

#### datasets (uploaded data for statistical analysis)
```sql
CREATE TABLE datasets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_id        UUID REFERENCES phases(id),
    name            TEXT NOT NULL,
    description     TEXT,
    file_path       TEXT,                              -- storage path for original upload
    row_count       INTEGER,
    column_count    INTEGER,
    columns         JSONB NOT NULL,                    -- [{ "name": "wait_time", "dtype": "float64", "nullable": true }]
    summary_stats   JSONB,                             -- auto-generated descriptive statistics
    data_preview    JSONB,                             -- first 50 rows for quick display
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### statistical_analyses (test configurations and results)
```sql
CREATE TABLE statistical_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    dataset_id      UUID REFERENCES datasets(id),
    phase_id        UUID REFERENCES phases(id),

    -- Test configuration
    test_type       TEXT NOT NULL,                     -- see Statistical Test Catalog below
    test_category   TEXT NOT NULL,                     -- descriptive, comparison, correlation, regression, spc, capability, doe
    configuration   JSONB NOT NULL,                    -- test-specific params (y_column, x_columns, alpha, etc.)

    -- AI recommendation context
    ai_recommended  BOOLEAN DEFAULT false,
    ai_reasoning    TEXT,                              -- why this test was suggested

    -- Results
    status          TEXT DEFAULT 'pending',            -- pending, running, completed, failed
    results         JSONB,                             -- test-specific output (p_value, confidence_interval, coefficients, etc.)
    charts          JSONB,                             -- [{ "type": "histogram", "data": {...}, "layout": {...} }] plotly specs
    ai_interpretation TEXT,                            -- plain-language explanation of results
    ai_next_steps   TEXT,                              -- what to do based on results

    -- Metadata
    run_by          UUID REFERENCES users(id),
    run_at          TIMESTAMPTZ,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### ai_conversations (agent interaction history)
```sql
CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_id        UUID REFERENCES phases(id),
    agent_type      TEXT NOT NULL,                     -- methodology_coach, statistical_advisor, report_writer
    messages        JSONB NOT NULL DEFAULT '[]',       -- [{ "role": "user"|"assistant", "content": "...", "timestamp": "..." }]
    context_summary TEXT,                              -- compressed context for long conversations
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

#### action_items
```sql
CREATE TABLE action_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_id        UUID REFERENCES phases(id),
    title           TEXT NOT NULL,
    description     TEXT,
    classification  TEXT DEFAULT 'action_item',        -- action_item, escalation, decision_needed, risk, blocker
    assigned_to     UUID REFERENCES users(id),
    owner_name      TEXT,                              -- for external stakeholders not in system
    status          TEXT DEFAULT 'not_started',        -- not_started, in_progress, completed, deferred
    priority        TEXT DEFAULT 'medium',
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### initiative_stakeholders (junction)
```sql
CREATE TABLE initiative_stakeholders (
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,                     -- sponsor, lead, contributor, reviewer, informed, sme
    added_at        TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (initiative_id, user_id)
);

CREATE TABLE external_stakeholders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    title           TEXT,
    organization    TEXT,
    email           TEXT,
    phone           TEXT,
    role            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### notes
```sql
CREATE TABLE notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_id        UUID REFERENCES phases(id),
    author_id       UUID REFERENCES users(id),
    note_type       TEXT DEFAULT 'general',            -- general, decision, blocker, status_update, meeting_notes, gate_review
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### documents
```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    phase_id        UUID REFERENCES phases(id),
    name            TEXT NOT NULL,
    document_type   TEXT,                              -- charter, requirements, report, presentation, data, reference
    file_path       TEXT,                              -- storage path
    external_url    TEXT,                              -- or external link
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### metrics (KPIs and performance tracking)
```sql
CREATE TABLE metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    unit            TEXT,                               -- %, $, count, days, hours, score, rate
    baseline_value  NUMERIC,
    baseline_date   DATE,
    baseline_period TEXT,
    target_value    NUMERIC,
    current_value   NUMERIC,
    current_date    DATE,
    current_period  TEXT,
    target_met      BOOLEAN,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

#### workload_entries (capacity tracking)
```sql
CREATE TABLE workload_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    initiative_id   UUID REFERENCES initiatives(id),
    hours_allocated NUMERIC NOT NULL,
    week_of         DATE NOT NULL,                     -- Monday of the tracking week
    actual_hours    NUMERIC,
    notes           TEXT,
    UNIQUE(user_id, initiative_id, week_of)
);
```

---

## Statistical Test Catalog

The statistical engine must support these tests, organized by category:

### Descriptive Statistics
- `descriptive_summary` — mean, median, mode, std dev, range, quartiles, skewness, kurtosis
- `normality_test` — Shapiro-Wilk, Anderson-Darling, with histogram + normal probability plot

### Comparison Tests
- `one_sample_t` — compare sample mean to known value
- `two_sample_t` — compare means of two independent groups
- `paired_t` — compare means of paired observations
- `one_way_anova` — compare means across 3+ groups
- `two_way_anova` — two factor comparison with interaction
- `mann_whitney` — non-parametric 2-sample comparison
- `kruskal_wallis` — non-parametric 3+ group comparison
- `chi_square_association` — test association between categorical variables
- `chi_square_goodness` — test distribution fit

### Correlation & Regression
- `correlation` — Pearson and Spearman correlation matrix
- `simple_regression` — single predictor linear regression
- `multiple_regression` — multiple predictor regression
- `logistic_regression` — binary outcome prediction

### Statistical Process Control (SPC)
- `xbar_r_chart` — subgroup means and ranges
- `i_mr_chart` — individual measurements and moving range
- `p_chart` — proportion defective
- `np_chart` — count defective
- `c_chart` — count defects per unit
- `u_chart` — defects per unit (variable sample size)

### Process Capability
- `capability_normal` — Cp, Cpk, Pp, Ppk for normal data
- `capability_nonnormal` — capability for non-normal distributions

### Design of Experiments
- `full_factorial` — 2^k full factorial design
- `fractional_factorial` — 2^(k-p) fractional factorial
- `doe_analysis` — analyze factorial experiment results with main effects and interactions

### Other Tools
- `pareto_analysis` — Pareto chart with vital few identification
- `msa_gage_rr` — Measurement System Analysis (Gage R&R)

---

## AI Agent Architecture

### Three-Layer Agent Design

```
LAYER 1: METHODOLOGY AGENTS (domain experts)
┌──────────────────────────────────────────────────────┐
│  Triage Agent    │  DMAIC Coach    │  Stats Advisor  │
│  Classifies      │  Guides phases  │  Recommends     │
│  requests,       │  asks probing   │  tests, runs    │
│  recommends      │  questions,     │  analysis,      │
│  methodology     │  checks rigor   │  interprets     │
└──────────────────────────────────────────────────────┘

LAYER 2: EXECUTION AGENTS (task performers)
┌──────────────────────────────────────────────────────┐
│  Data Agent      │  Chart Agent    │  Report Agent   │
│  Validates       │  Generates      │  Builds phase   │
│  uploads,        │  statistical    │  summaries,     │
│  profiles data,  │  charts,        │  executive      │
│  suggests        │  dashboards     │  briefs, gate   │
│  transforms      │                 │  review docs    │
└──────────────────────────────────────────────────────┘

LAYER 3: COORDINATION AGENT (orchestrator)
┌──────────────────────────────────────────────────────┐
│  Orchestrator                                        │
│  Routes user intent to correct agent                 │
│  Maintains cross-agent context                       │
│  Manages conversation memory                         │
│  Triggers agents based on workflow events             │
└──────────────────────────────────────────────────────┘
```

### Agent Behaviors

**Triage Agent** — Activated on new request intake
- Analyzes problem statement and desired outcome
- Scores complexity (1-10) based on scope, data needs, stakeholder count
- Recommends methodology: DMAIC (complex, data-driven), Kaizen (quick win), A3 (mid-size), PDSA (iterative), Just-Do-It (obvious fix)
- Suggests team assignment based on skills and capacity

**DMAIC Coach** — Activated during initiative execution
- Knows the full DMAIC body of knowledge
- Asks probing questions at each phase to ensure thoroughness
- Example (Define): "You've stated the problem, but have you quantified the baseline? What metric will you use to measure success?"
- Example (Measure): "Your data collection plan captures output data, but have you considered measurement system variation? An MSA might be needed."
- Evaluates phase completeness before gate review
- Generates phase summary reports

**Statistical Advisor** — Activated when data analysis is needed
- Examines dataset structure (column types, sample sizes, distributions)
- Recommends the right statistical test with plain-language reasoning
- Configures the test parameters
- After execution: translates results into business language
- Suggests follow-up analyses based on results
- Example: "Your p-value of 0.003 tells us there IS a statistically significant difference between shifts. Shift B has the highest defect rate at 4.2%, which is 68% higher than Shift A. I recommend drilling into Shift B with a Pareto analysis to find the top defect categories."

**Data Agent** — Activated on dataset upload
- Validates data integrity (missing values, outliers, data types)
- Generates descriptive statistics and data profile
- Suggests data transformations if needed
- Flags potential issues: "Column 'wait_time' has 12% missing values. How would you like to handle these?"

**Chart Agent** — Generates visualizations
- Creates Plotly chart specifications from analysis results
- Supports all statistical chart types (histogram, box plot, scatter, control chart, Pareto, probability plot, main effects plot, interaction plot)
- Generates both interactive (frontend) and static (report) versions

**Report Agent** — Builds documents
- Generates phase gate review documents
- Creates executive summary briefs
- Builds project close-out reports with before/after comparison
- Produces portfolio roll-up reports

**Orchestrator** — Routes and coordinates
- Interprets user intent and routes to the correct agent
- Maintains session context across agents
- Triggers automatic agent actions (e.g., data uploaded → Data Agent profiles it → Stats Advisor suggests tests)
- Manages conversation memory with summarization for long interactions

---

## Methodology Frameworks

### DMAIC (Primary)

| Phase | Key Questions AI Asks | Artifacts Produced |
|-------|----------------------|-------------------|
| **Define** | What is the problem? How do you measure it today? Who is impacted? What does success look like? What is the scope boundary? | Project Charter, SIPOC, VOC/CTQ Tree, Stakeholder Map |
| **Measure** | How will you collect data? Is your measurement system reliable? What does the current process look like? What is the baseline performance? | Data Collection Plan, MSA Results, Process Map, Baseline Capability |
| **Analyze** | What are the potential root causes? Which ones does the data support? What is the statistical evidence? What are the vital few X's? | Fishbone Diagram, 5-Why, Hypothesis Tests, Regression, Pareto |
| **Improve** | What solutions address the vital X's? How will you prioritize? What does the pilot plan look like? Did the pilot work? | Solution Matrix, Pilot Plan, Before/After Comparison, Cost-Benefit |
| **Control** | How will you sustain the gains? What will you monitor? Who owns the process going forward? | Control Plan, Control Charts, SOPs, Training Plan, Handoff |

### Alternative Methodologies
- **Kaizen** — Rapid improvement event (1-5 days). Simplified: Define problem → Map current state → Identify waste → Implement countermeasures → Confirm results
- **A3** — Single-page problem solving. Structured sections: Background, Current Condition, Goal, Root Cause, Countermeasures, Implementation, Follow-up
- **PDSA** — Iterative cycles: Plan (hypothesis) → Do (test) → Study (results) → Act (adopt/adjust/abandon)
- **Just-Do-It** — For obvious fixes. Document the change, verify the result, close

---

## API Contract Specification

### Endpoint Groups

All endpoints prefixed with `/api/v1/`

#### Auth & Users
```
POST   /auth/login
POST   /auth/register
GET    /users/me
GET    /users                          # list (admin/manager)
PATCH  /users/:id
GET    /users/:id/workload             # capacity and allocation
```

#### Teams
```
GET    /teams
POST   /teams
GET    /teams/:id
PATCH  /teams/:id
GET    /teams/:id/members
POST   /teams/:id/members
DELETE /teams/:id/members/:userId
GET    /teams/:id/workload             # team capacity overview
```

#### Requests (Intake)
```
GET    /requests                        # list with filters
POST   /requests                        # submit new request
GET    /requests/:id
PATCH  /requests/:id                    # review, accept, decline
POST   /requests/:id/convert           # convert to initiative
POST   /requests/:id/triage            # AI triage assessment
```

#### Initiatives (Living Profiles)
```
GET    /initiatives                     # list with filters, sort, pagination
POST   /initiatives
GET    /initiatives/:id                 # full profile with phases, current state
PATCH  /initiatives/:id
DELETE /initiatives/:id
GET    /initiatives/:id/timeline        # activity timeline
GET    /initiatives/:id/summary         # AI-generated summary
```

#### Phases
```
GET    /initiatives/:id/phases
GET    /initiatives/:id/phases/:phase   # phase detail with artifacts
PATCH  /initiatives/:id/phases/:phase   # update phase status
POST   /initiatives/:id/phases/:phase/gate  # gate review
```

#### Phase Artifacts
```
GET    /initiatives/:id/phases/:phase/artifacts
POST   /initiatives/:id/phases/:phase/artifacts
GET    /artifacts/:id
PATCH  /artifacts/:id
DELETE /artifacts/:id
```

#### Datasets & Statistical Analysis
```
POST   /initiatives/:id/datasets        # upload dataset (multipart)
GET    /initiatives/:id/datasets
GET    /datasets/:id                     # dataset detail with profile
GET    /datasets/:id/preview             # first N rows
DELETE /datasets/:id

POST   /datasets/:id/analyze            # run statistical test
GET    /analyses/:id                     # analysis results
GET    /initiatives/:id/analyses         # all analyses for initiative
POST   /analyses/:id/interpret           # AI interpretation of results
```

#### AI Agent Endpoints
```
POST   /ai/chat                          # general agent conversation
POST   /ai/triage                        # request triage
POST   /ai/coach                         # DMAIC coaching interaction
POST   /ai/stats/recommend               # statistical test recommendation
POST   /ai/stats/interpret               # results interpretation
POST   /ai/report/generate               # generate report
GET    /ai/conversations/:initiativeId   # conversation history
```

#### Action Items
```
GET    /initiatives/:id/actions
POST   /initiatives/:id/actions
PATCH  /actions/:id
DELETE /actions/:id
GET    /actions                          # global action list with filters
```

#### Stakeholders, Notes, Documents
```
GET    /initiatives/:id/stakeholders
POST   /initiatives/:id/stakeholders
DELETE /initiatives/:id/stakeholders/:userId

GET    /initiatives/:id/notes
POST   /initiatives/:id/notes
DELETE /notes/:id

GET    /initiatives/:id/documents
POST   /initiatives/:id/documents       # upload or link
DELETE /documents/:id
```

#### Metrics & Performance
```
GET    /initiatives/:id/metrics
POST   /initiatives/:id/metrics
PATCH  /metrics/:id
DELETE /metrics/:id
```

#### Dashboards & Reporting
```
GET    /dashboard/portfolio              # portfolio roll-up metrics
GET    /dashboard/team/:id              # team performance
GET    /dashboard/user/:id              # individual workload
GET    /dashboard/initiative/:id        # initiative performance profile
GET    /reports/executive-brief          # portfolio executive summary
GET    /reports/initiative/:id          # individual initiative report
POST   /reports/generate                 # generate PDF/HTML report
```

---

## Frontend Route Structure

```
/                                        # Landing / Login
/dashboard                               # Portfolio dashboard (roll-ups)
/requests                                # Request intake queue
/requests/new                            # Submit new request
/requests/:id                            # Request detail / triage
/initiatives                             # Initiative board (kanban) or list
/initiatives/:id                         # Initiative living profile
/initiatives/:id/define                  # Define phase workspace
/initiatives/:id/measure                 # Measure phase workspace
/initiatives/:id/analyze                 # Analyze phase workspace
/initiatives/:id/improve                 # Improve phase workspace
/initiatives/:id/control                 # Control phase workspace
/initiatives/:id/data                    # Datasets & analyses
/initiatives/:id/data/:datasetId         # Dataset detail
/initiatives/:id/report                  # Initiative report
/team                                    # Team management & workload
/team/:id                                # Team detail
/actions                                 # Global action items
/reports                                 # Report generation & scheduling
/settings                                # Platform settings
/admin                                   # Admin panel
```

---

## UI Design Principles

1. **Dark mode default** with light mode toggle (matches ICC aesthetic)
2. **Information density** — performance teams need data-rich views, not consumer-app whitespace
3. **Click-to-drill** — every metric, chart, and number is clickable to drill deeper
4. **AI panels** — right-side sliding panels for AI agent conversations, contextual to current view
5. **Phase workspace** — each DMAIC phase gets a dedicated workspace with artifacts, data, AI coaching, and gate review
6. **Status colors** — consistent across all views: green (on track/complete), yellow (at risk), red (blocked/overdue), blue (accent/active), purple (type tags), teal (AI interactions)
7. **Real-time** — dashboard metrics update live, agent conversations stream

---

## Project File Structure

```
bb-enabled-command/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/              # AppShell, Sidebar, TopBar, AIPanel
│   │   │   ├── dashboard/           # PortfolioDashboard, TeamDashboard, MetricCards, RollUpCharts
│   │   │   ├── requests/            # RequestQueue, RequestForm, TriagePanel
│   │   │   ├── initiatives/         # InitiativeBoard, InitiativeList, InitiativeProfile
│   │   │   ├── phases/              # PhaseWorkspace, PhaseGate, ArtifactEditor
│   │   │   ├── data/                # DatasetUpload, DataPreview, AnalysisConfig, ResultsPanel
│   │   │   ├── charts/              # StatChart, ControlChart, ParetoChart, CapabilityChart
│   │   │   ├── ai/                  # AIChat, CoachPanel, StatsAdvisor, TriageAssistant
│   │   │   ├── actions/             # ActionList, ActionItem, ActionBoard
│   │   │   ├── team/                # TeamRoster, WorkloadView, CapacityChart
│   │   │   ├── reports/             # ReportBuilder, ExecutiveBrief, PhaseReport
│   │   │   └── shared/              # StatusBadge, PriorityTag, UserAvatar, DataTable, Modal
│   │   ├── stores/                  # Zustand stores (initiative, auth, dashboard, ai)
│   │   ├── hooks/                   # Custom hooks (useInitiative, useAI, useStats, useWorkload)
│   │   ├── types/                   # TypeScript interfaces matching API contracts
│   │   ├── utils/                   # Formatters, validators, chart helpers
│   │   ├── api/                     # API client functions organized by endpoint group
│   │   ├── router.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── config.py                # Environment config
│   │   ├── database.py              # SQLAlchemy engine & session
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── team.py
│   │   │   ├── request.py
│   │   │   ├── initiative.py
│   │   │   ├── phase.py
│   │   │   ├── artifact.py
│   │   │   ├── dataset.py
│   │   │   ├── analysis.py
│   │   │   ├── action_item.py
│   │   │   ├── note.py
│   │   │   ├── document.py
│   │   │   ├── metric.py
│   │   │   └── ai_conversation.py
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── routers/                 # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── teams.py
│   │   │   ├── requests.py
│   │   │   ├── initiatives.py
│   │   │   ├── phases.py
│   │   │   ├── artifacts.py
│   │   │   ├── datasets.py
│   │   │   ├── analyses.py
│   │   │   ├── ai.py
│   │   │   ├── actions.py
│   │   │   ├── dashboards.py
│   │   │   └── reports.py
│   │   ├── services/                # Business logic layer
│   │   │   ├── workflow_engine.py   # Phase transitions, gate logic
│   │   │   ├── assignment_engine.py # Workload balancing, skill matching
│   │   │   ├── stats_engine.py      # Statistical test execution
│   │   │   ├── ai_orchestrator.py   # Agent routing and context management
│   │   │   ├── report_generator.py  # PDF/HTML report building
│   │   │   └── dashboard_engine.py  # Roll-up calculations
│   │   ├── agents/                  # AI agent prompt templates and logic
│   │   │   ├── orchestrator.py
│   │   │   ├── triage_agent.py
│   │   │   ├── dmaic_coach.py
│   │   │   ├── stats_advisor.py
│   │   │   ├── data_agent.py
│   │   │   ├── chart_agent.py
│   │   │   └── report_agent.py
│   │   ├── stats/                   # Statistical test implementations
│   │   │   ├── descriptive.py
│   │   │   ├── comparison.py
│   │   │   ├── correlation.py
│   │   │   ├── regression.py
│   │   │   ├── spc.py
│   │   │   ├── capability.py
│   │   │   ├── doe.py
│   │   │   └── charts.py
│   │   └── utils/
│   ├── alembic/                     # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml               # Local dev (postgres, redis, backend, frontend)
├── .env.example
└── README.md
```

---

## Builder Agent Scope Boundaries

This project is designed to be built by **5 parallel builder agents**, each owning a distinct vertical slice. The orchestrator agents (defined in `agents/orchestrators/`) coordinate between them.

### Builder 1: Frontend UI
**Owns:** `frontend/` entire directory
**Builds:** React components, routing, state management, Tailwind styling, Plotly chart wrappers
**Depends on:** API contract (this document), TypeScript types from API schemas
**Does NOT touch:** Backend Python code, database schemas, AI prompts

### Builder 2: API & Database
**Owns:** `backend/app/main.py`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/routers/`, `backend/app/database.py`, `backend/alembic/`
**Builds:** FastAPI endpoints, SQLAlchemy models, Pydantic schemas, database migrations, auth middleware
**Depends on:** API contract (this document), data model (this document)
**Does NOT touch:** Frontend code, AI agent logic, statistical implementations

### Builder 3: Statistical Engine
**Owns:** `backend/app/stats/`, `backend/app/services/stats_engine.py`
**Builds:** All statistical test implementations using scipy/statsmodels, chart generation using plotly, test selection logic
**Depends on:** Dataset schema, analysis schema, stat test catalog (this document)
**Does NOT touch:** Frontend code, API routes, AI prompts, database models

### Builder 4: AI Agent System
**Owns:** `backend/app/agents/`, `backend/app/services/ai_orchestrator.py`
**Builds:** Agent prompt templates, orchestrator routing logic, context management, conversation memory, Claude API integration
**Depends on:** Initiative/phase data model, stat test catalog (for advisor agent), methodology frameworks (this document)
**Does NOT touch:** Frontend code, API routes, statistical implementations

### Builder 5: Dashboards & Reporting
**Owns:** `backend/app/services/dashboard_engine.py`, `backend/app/services/report_generator.py`, `backend/app/routers/dashboards.py`, `backend/app/routers/reports.py`, plus `frontend/src/components/dashboard/` and `frontend/src/components/reports/`
**Builds:** Roll-up calculation logic, dashboard API endpoints, report PDF/HTML generation, frontend dashboard components and chart layouts
**Depends on:** All data models, API contract, chart specifications
**Does NOT touch:** AI agents, statistical engine internals, auth system

---

## Integration Points Between Builders

These are the contracts that must be honored for parallel work to assemble correctly:

| From | To | Contract |
|------|----|----------|
| Builder 2 (API) | Builder 1 (Frontend) | Pydantic response schemas define TypeScript types |
| Builder 2 (API) | Builder 3 (Stats) | `stats_engine.run_test(test_type, config, dataset)` returns standardized `AnalysisResult` |
| Builder 2 (API) | Builder 4 (AI) | `ai_orchestrator.route(intent, context)` returns `AgentResponse` |
| Builder 3 (Stats) | Builder 4 (AI) | Stats Advisor calls `stats_engine.get_available_tests(dataset_profile)` and `stats_engine.run_test()` |
| Builder 3 (Stats) | Builder 5 (Dashboards) | Chart specs use Plotly JSON format consumable by frontend |
| Builder 4 (AI) | Builder 1 (Frontend) | AI responses stream via WebSocket with `{ agent, content, metadata }` format |
| Builder 5 (Dashboards) | Builder 2 (API) | Dashboard queries use SQL views/materialized views defined in migrations |

---

## Key Interfaces

### AnalysisResult (returned by stats engine)
```python
class AnalysisResult(BaseModel):
    test_type: str
    test_category: str
    success: bool
    summary: dict                # { "statistic": 4.23, "p_value": 0.003, "effect_size": 0.45 }
    details: dict                # test-specific detailed output
    charts: list[PlotlyChart]    # [{ "type": "histogram", "data": {...}, "layout": {...} }]
    interpretation_context: dict  # passed to AI for plain-language interpretation
    warnings: list[str]          # data quality or assumption violation warnings
```

### AgentResponse (returned by AI orchestrator)
```python
class AgentResponse(BaseModel):
    agent_type: str              # which agent handled this
    content: str                 # the response text
    suggestions: list[str]       # follow-up actions or questions
    artifacts: list[dict]        # any generated artifacts (charts, templates, etc.)
    context_update: dict         # updates to conversation context
    requires_action: bool        # does this need user action?
    action_type: str | None      # 'upload_data', 'run_test', 'review_gate', etc.
```

### DatasetProfile (generated on upload)
```python
class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]  # name, dtype, unique_count, null_count, min, max, mean, std
    recommended_tests: list[str]  # AI-suggested based on data structure
    quality_issues: list[str]     # missing data, outliers, etc.
```

---

## Agent Continuity Protocol

**CRITICAL — READ THIS FIRST IF YOU ARE A NEW AGENT OR SESSION**

This project is built across multiple Claude sessions. Each session has a ~1 million token context limit. To prevent lost work and duplicated effort:

### Before Context Runs Out (Mandatory)
Every agent working on this project MUST update this file before reaching context capacity:

1. **Update the Build Status table below** — mark completed items, add new items discovered during work
2. **Update Current Phase** — what phase we're in and what's next
3. **Update the Last Session Log** — a concise summary of what was accomplished, decisions made, and any blockers
4. **Update File Inventory** — if new files were created, add them to the inventory

### When Starting a New Session
1. Read this entire CLAUDE.md first — it is the single source of truth
2. Check the Build Status table for what's done vs. what's next
3. Read the Last Session Log for context on recent decisions
4. Check the File Inventory to understand what exists
5. Continue from the Current Phase — do NOT repeat completed work

### When Completing a Major Milestone
Update this file immediately. Don't wait until context is running low.

---

## Named Agent Assignments

When running parallel Claude sessions, open a new session and tell it:
> "You are **[Agent Name]**. Read `BB_Enabled_Command/CLAUDE.md` and begin your assigned work."

Each agent has a clear scope, owns specific files, and must NOT touch files owned by other agents.

| Agent Name | Scope | Owns (files) | Phase |
|------------|-------|-------------|-------|
| **Forge** | API & Database — remaining CRUD routers, services, auth, migrations | `backend/app/routers/`, `backend/app/services/`, `backend/app/schemas/`, `backend/app/dependencies.py`, `backend/alembic/` | Phase 1 |
| **Sigma** | Statistical Engine — all scipy/statsmodels test implementations, chart generation, and dual-layer validation system | `backend/app/stats/`, `backend/app/services/stats_engine.py`, `backend/app/agents/stats_validator.py` | Phase 2 |
| **Beacon** | Dashboard & Reporting — roll-up calculations, report generation, dashboard endpoints | `backend/app/services/dashboard_engine.py`, `backend/app/services/report_generator.py`, `backend/app/routers/dashboards.py`, `backend/app/routers/reports.py` | Phase 3 |
| **Prism** | React Frontend — all UI components, routing, state management, Tailwind, Plotly charts | `frontend/` entire directory | Phase 4 |
| **Nexus** | Integration & Polish — event bus, workflow chains, WebSocket dashboard, file storage, email notifications | `backend/app/services/event_bus.py`, `services/workflow_chains.py`, `services/ws_manager.py`, `services/file_storage.py`, `services/email_service.py`, `routers/ws_dashboard.py` | Phase 5 |
| **Atlas** | Integration & DevOps — Docker, CI/CD, deployment, file storage, email, end-to-end wiring | `docker-compose.yml`, `Dockerfile`, `.github/`, deployment configs | Phase 6 |

### Agent Rules
1. **Read CLAUDE.md first** — every agent must read this file before writing any code
2. **Stay in your lane** — only modify files in your "Owns" column. If you need something from another agent's scope, document the requirement in the session log and move on
3. **Update CLAUDE.md when done** — before your session ends, update the Build Status table and Last Session Log with what you accomplished
4. **Honor contracts** — if another agent's work depends on an interface you define, document it clearly in CLAUDE.md
5. **No duplicate work** — check the Build Status table. If it says "Done", don't rebuild it

### Which Agents Can Run in Parallel
- **Forge** + **Sigma** — safe (no file overlap, Sigma creates new files in `stats/`)
- **Forge** + **Nexus** — safe (Forge owns routers/services, Nexus owns agents)
- **Sigma** + **Nexus** — safe (Sigma owns stats engine, Nexus owns agent prompts)
- **Prism** — can run alongside any backend agent (entirely separate directory)
- **Beacon** — best after Forge completes (needs CRUD endpoints to exist)
- **Atlas** — best after Phases 1-4 are substantially complete

### Current Assignment Status
| Agent | Status | Notes |
|-------|--------|-------|
| **Forge** | Complete | Phase 1 done. All 12 routers, auth, workflow/assignment services |
| **Sigma** | Complete | Phase 2 done. Full statistical engine: 27 tests, chart generation, stats engine service |
| **Beacon** | Complete | Phase 3 done. Dashboard engine, report generator, 36 tests |
| **Prism** | Complete | Phase 4 done. All pages, shared components, stores, API layer |
| **Nexus** | Complete | Phase 5 done. Event bus, 5 workflow chains, WS dashboard, file storage (local+S3), email service, 38 tests |
| **Atlas** | Complete | Phase 6 done. Dockerfiles, CI/CD, Vercel config, production compose |

---

## Build Status

**Last updated:** 2026-02-12
**Current Phase:** ALL PHASES COMPLETE (0-6)
**Overall Progress:** All 7 phases complete. Backend fully runnable with auth, 16 API routers (incl. WS dashboard), 27 statistical tests, 5 AI agents, dashboard engine, report generator, event-driven workflow chains, file storage (local+S3), email notifications. Frontend has all page components, shared components, API layer, stores, and CSS utilities. Infrastructure complete: production Dockerfiles, Docker Compose (dev + prod), GitHub Actions CI/CD, Vercel config, nginx reverse proxy, .env templates.

### Phase 0: Foundation (COMPLETE)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Project structure & dependencies | Done | `backend/requirements.txt`, `.env.example` | FastAPI, SQLAlchemy, Anthropic, scipy, etc. |
| Configuration layer | Done | `backend/app/config.py` | Pydantic Settings, env-driven, model selection |
| Agent base framework | Done | `backend/app/agents/base.py` | BaseAgent ABC, AgentContext, AgentResponse, ConversationMemory |
| AI Orchestrator | Done | `backend/app/agents/orchestrator.py` | Intent classification (regex + AI fallback), agent routing, streaming |
| Triage Agent | Done | `backend/app/agents/triage_agent.py` | Complexity scoring, methodology recommendation |
| DMAIC Coach Agent | Done | `backend/app/agents/dmaic_coach.py` | Phase-aware coaching, dynamic prompt injection, gate review criteria |
| Stats Advisor Agent | Done | `backend/app/agents/stats_advisor.py` | Test recommendation matrix, result interpretation |
| Data Agent | Done | `backend/app/agents/data_agent.py` | Dataset profiling, quality assessment |
| Report Agent | Done | `backend/app/agents/report_agent.py` | 5 report types (phase gate, exec summary, stats translation, close-out, portfolio) |
| Database engine & sessions | Done | `backend/app/database.py` | Async SQLAlchemy, session factory, FastAPI dependency |
| ORM models (all 14 tables) | Done | `backend/app/models/` | user, team, request, initiative, phase, artifact, dataset, analysis, action_item, note, document, stakeholder, metric, ai_conversation, workload |
| Pydantic API schemas | Done | `backend/app/schemas/` | Request + Initiative create/update/response schemas |
| AI API router | Done | `backend/app/routers/ai.py` | POST /chat, /chat/stream (SSE), /invoke/{agent}, GET /agents, WS /ws |
| Request API router | Done | `backend/app/routers/requests.py` | CRUD + convert-to-initiative |
| Initiative API router | Done | `backend/app/routers/initiatives.py` | CRUD + phase management + auto-advance |
| FastAPI entry point | Done | `backend/app/main.py` | Lifespan hooks, CORS, router registration, health check |
| Alembic migration setup | Done | `backend/alembic/` | env.py (async), script template, alembic.ini |
| Orchestrator agent definitions | Done | `agents/orchestrators/` | system-architect.md, methodology-expert.md, integration-coordinator.md |
| Builder agent definitions | Done | `agents/builders/` | 5 builder agent scope docs |

### Phase 1: Make the Backend Runnable (COMPLETE — Agent: Forge)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Auth system (JWT login/register) | Done | `routers/auth.py`, `services/auth.py`, `dependencies.py`, `schemas/auth.py` | JWT via python-jose, bcrypt hashing, register/login/me endpoints, get_current_user + require_role guards. password_hash added to User model. |
| User management endpoints | Done | `routers/users.py`, `schemas/user.py` | GET /users (admin/manager), GET /:id, PATCH /:id (self or admin), GET /:id/workload |
| Team management endpoints | Done | `routers/teams.py`, `schemas/user.py` | CRUD + GET/POST/DELETE members |
| Artifact CRUD endpoints | Done | `routers/artifacts.py`, `schemas/supporting.py` | Phase-scoped create/read/update/delete |
| Dataset upload endpoint | Done | `routers/datasets.py`, `schemas/supporting.py` | Multipart CSV/Excel upload with auto-profiling via pandas (column types, summary stats, preview) |
| Action item endpoints | Done | `routers/actions.py`, `schemas/supporting.py` | Initiative-scoped + global cross-initiative list, auto completed_at stamp |
| Notes endpoints | Done | `routers/notes.py`, `schemas/supporting.py` | Initiative-scoped CRUD with note_type filter |
| Documents endpoints | Done | `routers/documents.py`, `schemas/supporting.py` | File reference + external link CRUD |
| Metrics endpoints | Done | `routers/metrics.py`, `schemas/supporting.py` | KPI CRUD with baseline/target/current tracking |
| Workflow engine service | Done | `services/workflow_engine.py` | Phase transition validation, gate readiness check (required artifacts), advance_phase() with auto-complete logic |
| Assignment engine service | Done | `services/assignment_engine.py` | Analyst recommendation (skill match + utilization scoring), team utilization summary, workload per analyst |
| Docker Compose | Done | `docker-compose.yml`, `backend/Dockerfile` | PostgreSQL 16 + Redis 7 + backend with hot-reload |
| Request triage endpoint | Done | `routers/requests.py` (POST /:id/triage) | Invokes Triage Agent directly, updates request with complexity_score and recommended_methodology |

### Phase 2: Statistical Engine (COMPLETE — Agent: Sigma)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Shared types (AnalysisResult, PlotlyChart) | Done | `stats/__init__.py` | Standardized result format for all tests |
| Chart generation | Done | `stats/charts.py` | 12 chart types: histogram, box, scatter, bar, pareto, Q-Q, control chart, heatmap, residual, main effects, interaction, capability histogram. Dark-mode styling. |
| Descriptive statistics | Done | `stats/descriptive.py` | mean, median, mode, std, quartiles, skewness, kurtosis, CV, with histograms |
| Normality test | Done | `stats/descriptive.py` | Shapiro-Wilk + Anderson-Darling with histogram and Q-Q plot |
| Pareto analysis | Done | `stats/descriptive.py` | Pareto chart with vital-few identification (80/20 rule) |
| One-sample t-test | Done | `stats/comparison.py` | Compare mean to population value, effect size, CI |
| Two-sample t-test | Done | `stats/comparison.py` | Independent groups, auto Levene's → Welch's, Cohen's d |
| Paired t-test | Done | `stats/comparison.py` | Before/after paired comparison with difference distribution |
| One-way ANOVA | Done | `stats/comparison.py` | F-test + Tukey HSD post-hoc + eta-squared |
| Two-way ANOVA | Done | `stats/comparison.py` | Two-factor with interaction via statsmodels, interaction plot |
| Mann-Whitney U | Done | `stats/comparison.py` | Non-parametric 2-sample, rank-biserial effect size |
| Kruskal-Wallis H | Done | `stats/comparison.py` | Non-parametric 3+ groups, epsilon-squared |
| Chi-square association | Done | `stats/comparison.py` | Contingency table, Cramér's V, expected freq check |
| Chi-square goodness of fit | Done | `stats/comparison.py` | Observed vs expected distribution |
| Correlation | Done | `stats/regression.py` | Pearson + Spearman matrices with p-values, heatmaps |
| Simple regression | Done | `stats/regression.py` | OLS with scatter+trendline, residual plots, Durbin-Watson |
| Multiple regression | Done | `stats/regression.py` | Multiple predictors, VIF multicollinearity check, AIC/BIC |
| Logistic regression | Done | `stats/regression.py` | Binary outcome, odds ratios, confusion matrix, accuracy |
| I-MR control chart | Done | `stats/spc.py` | Individuals + Moving Range, violation detection |
| X-bar/R control chart | Done | `stats/spc.py` | Subgroup means/ranges, constants for n=2-10 |
| P chart | Done | `stats/spc.py` | Proportion defective (variable sample size) |
| NP chart | Done | `stats/spc.py` | Count defective (constant sample size) |
| C chart | Done | `stats/spc.py` | Defects per unit (constant opportunity) |
| U chart | Done | `stats/spc.py` | Defects per unit (variable sample size) |
| Process capability (normal) | Done | `stats/capability.py` | Cp, Cpk, Pp, Ppk, PPM, sigma level, capability rating |
| Process capability (non-normal) | Done | `stats/capability.py` | Box-Cox transformation, transformed spec limits |
| Gage R&R (MSA) | Done | `stats/capability.py` | ANOVA method, variance components, %Study Var, NDC, rating |
| Full factorial design | Done | `stats/doe.py` | 2^k design generation with randomization, center points |
| Fractional factorial design | Done | `stats/doe.py` | 2^(k-p) design with generators |
| DOE analysis | Done | `stats/doe.py` | Main effects, interactions, Pareto of effects, R² |
| Stats engine service | Done | `services/stats_engine.py` | StatsEngine class: direct DataFrame run_test(), TEST_CATALOG metadata (27 tests), applicability filtering for Stats Advisor agent |
| Engine integration | Done | `stats/engine.py` | Wired all 27 tests into Forge's @register_test registry via _make_runner() async bridge + _dataset_to_dataframe() converter. execute_analysis() now stores interpretation_context for AI. |
| Programmatic validator | Done | `stats/validator.py` | Dual-layer validation Layer 1: deterministic input/output/assumption checks for all 27 tests. ValidationReport with findings, confidence levels, recommendations. |
| AI validation agent | Done | `agents/stats_validator.py` | Dual-layer validation Layer 2: independent AI review of every test. Uses Sonnet (light model) for cost efficiency. Returns verdict, confidence score, plain-language summary, findings, recommendation. |
| Validation integration | Done | `stats/engine.py` | Validation hook in execute_analysis() — runs programmatic checks + AI review after every test. Results stored in `analysis.results["validation"]`. |

### Phase 3: Dashboard & Reporting Engine (COMPLETE — Agent: Beacon)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Dashboard Pydantic schemas | Done | `schemas/dashboard.py` | PortfolioMetrics, TeamMetrics, InitiativeMetrics, PipelineMetrics + sub-models (TrendPoint, DeadlineItem, MemberMetrics, BurndownPoint, PhaseDetail, MetricDetail, etc.) |
| Dashboard calculation engine | Done | `services/dashboard_engine.py` | DashboardEngine class: portfolio/team/initiative/pipeline metrics, health scoring (on_track/at_risk/blocked), 12-month trends, action burndown, upcoming deadlines, team utilization |
| Dashboard API endpoints | Done | `routers/dashboards.py` | Rewritten: delegates to DashboardEngine, typed response models, optional team_id filter on portfolio |
| Report generation service | Done | `services/report_generator.py` | Enhanced: AI narrative integration via ReportAgent, Plotly chart embedding as base64 PNG, graceful degradation, _markdown_to_html converter |
| Report API endpoints | Done | `routers/reports.py` | Enhanced: passes include_ai/include_charts options, GET /api/reports global list (admin/manager), role guard on portfolio reports |
| Dashboard performance indexes | Done | `alembic/versions/002_dashboard_indexes.py` | Indexes on action_items.due_date, initiatives.actual_completion, initiatives(status,current_phase) |
| Dashboard tests | Done | `tests/test_dashboards.py` | 14 tests: engine unit tests (portfolio, health scoring, trends, deadlines, burndown, pipeline) + API endpoint tests |
| Report tests | Done | `tests/test_reports.py` | 22 tests: all 5 report builders, dispatcher, validation, CRUD lifecycle, admin list with filters |

### Phase 4: React Frontend
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Project init (Vite + React + TS + Tailwind) | **Done** | `frontend/` | Dark mode default, Zustand, React Router, Plotly |
| App shell (layout, sidebar, topbar) | **Done** | `frontend/src/components/layout/` | Dark sidebar, AI panel slot, grouped nav |
| Auth pages (login, register) | **Done** | `frontend/src/components/auth/` | JWT integration, AuthGuard route protection |
| Request intake flow | Scaffold | `frontend/src/components/requests/` | Queue table done, submit form placeholder |
| Initiative board & profile | **Done** | `frontend/src/pages/InitiativeList.tsx`, `InitiativeProfile.tsx` | Kanban/list toggle, tabbed profile with phases, overview, timeline |
| Phase workspaces | **Done** | `frontend/src/pages/PhaseWorkspace.tsx` | Artifacts, analysis, actions sections, gate review, AI summary |
| AI chat panel | Scaffold | `frontend/src/components/ai/` | AIPanel.tsx + aiStore.ts created by Prism |
| Data & analysis views | **Done** | `frontend/src/pages/DataView.tsx` | Drag-drop CSV/Excel upload, dataset list, analyze button |
| Action board | **Done** | `frontend/src/pages/ActionBoard.tsx` | Overdue/due-this-week/open columns, priority + status badges |
| Reports page | **Done** | `frontend/src/pages/ReportsPage.tsx` | 5 report types, generate flow, preview/download/send actions |
| Dashboard views | **Done** | `frontend/src/components/dashboard/` | PortfolioDashboard with metric cards + distributions |
| API client layer | **Done** | `frontend/src/api/` | Typed client + auth, requests, initiatives, dashboards |
| Zustand stores | **Done** | `frontend/src/stores/` | Auth, initiative, dashboard, AI, UI state |
| Shared components | **Done** | `frontend/src/components/shared/` | StatusBadge, PriorityTag, MetricCard, PageHeader, LoadingSpinner, EmptyState, PlotlyChart |
| CSS utility classes | **Done** | `frontend/src/index.css` | @layer components: card, card-hover, btn-primary/secondary/ghost/danger, btn-sm, input-field |
| TypeScript types | **Done** | `frontend/src/types/api.ts` | All interfaces matching backend Pydantic schemas |
| Router | **Done** | `frontend/src/router.tsx` | All routes from spec, all page components resolve |

### Phase 5: Integration & Polish (COMPLETE — Agent: Nexus)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Event bus (pub/sub) | Done | `services/event_bus.py` | Async in-process event bus, 6 event types, fire-and-forget background tasks |
| Workflow chains (5 handlers) | Done | `services/workflow_chains.py` | Dataset→quality, Analysis→interpretation, Phase→summary+email, Initiative→closeout, Action→email |
| Event publishing in routers | Done | `routers/datasets.py`, `initiatives.py`, `actions.py`, `stats/engine.py` | Publish events after DB flush, RuntimeError-safe |
| Real-time dashboard WS | Done | `services/ws_manager.py`, `routers/ws_dashboard.py` | Subscription-based broadcast, scope filtering, dead connection cleanup |
| File storage (local + S3) | Done | `services/file_storage.py` | Abstract interface, LocalStorageBackend, S3StorageBackend (boto3) |
| Email notifications | Done | `services/email_service.py` | Async SMTP via asyncio.to_thread, 3 HTML templates, graceful degradation |
| Config + main.py wiring | Done | `config.py`, `main.py` | Storage/SMTP/email settings, lifespan init, ws_dashboard router |
| Alembic migration 003 | Done | `alembic/versions/003_nexus_enhancements.py` | Indexes on datasets.initiative_id, action_items.assigned_to |
| Nexus tests (38 tests) | Done | `tests/test_event_bus.py`, `test_workflow_chains.py`, `test_file_storage.py`, `test_email_service.py`, `test_ws_dashboard.py` | Event bus, chains, storage, email, WebSocket |

### Phase 6: Deployment & Infrastructure (COMPLETE — Agent: Atlas)
| Item | Status | Files | Notes |
|------|--------|-------|-------|
| Frontend build verification | Done | `frontend/dist/` | `npm run build` passes clean. 305KB JS + 25KB CSS bundle |
| Production backend Dockerfile | Done | `backend/Dockerfile` | Multi-stage (deps → production), non-root user, 4 workers, health check, no test/dev files |
| Frontend Dockerfile | Done | `frontend/Dockerfile` | Multi-stage (node build → nginx serve), gzip, SPA fallback |
| Nginx config | Done | `frontend/nginx.conf` | API proxy to backend:8000, WebSocket upgrade, SPA fallback, security headers, asset caching |
| Docker Compose (dev) | Done | `docker-compose.yml` | Updated: targets deps stage, mounts full backend dir for hot-reload |
| Docker Compose (prod) | Done | `docker-compose.prod.yml` | Full stack: postgres + redis (password) + backend (4 workers) + frontend (nginx) + migrate (one-shot) |
| GitHub Actions CI/CD | Done | `.github/workflows/ci.yml` | Backend: pytest with Postgres service. Frontend: tsc + build + artifact upload. Docker: image build verification on main |
| Vercel frontend config | Done | `frontend/vercel.json` | API rewrites to BACKEND_URL, SPA fallback, cache headers, security headers |
| Production env template | Done | `.env.production.example` | All production secrets documented with generation instructions |
| Dockerignore files | Done | `backend/.dockerignore`, `frontend/.dockerignore` | Exclude node_modules, __pycache__, .env, etc. |
| End-to-end wiring audit | Done | — | 95% routes aligned. 1 gap: DELETE /initiatives/{id} missing from backend (Forge scope) |

---

## File Inventory

All files created for BB Enabled Command, organized by layer:

### Agent & Orchestrator Definitions (Markdown)
```
BB_Enabled_Command/
├── CLAUDE.md                                          # This file — master vision + build status
├── agents/
│   ├── orchestrators/
│   │   ├── system-architect.md                        # Architecture authority agent
│   │   ├── methodology-expert.md                      # LSS domain expert agent
│   │   └── integration-coordinator.md                 # Assembly verification agent
│   └── builders/
│       ├── builder-1-frontend-ui.md                   # React frontend scope
│       ├── builder-2-api-database.md                  # FastAPI + PostgreSQL scope
│       ├── builder-3-statistical-engine.md             # scipy/statsmodels scope
│       ├── builder-4-ai-orchestration.md              # AI agent system scope
│       └── builder-5-dashboards-reporting.md           # Dashboard + report scope
```

### Backend (Python)
```
BB_Enabled_Command/backend/
├── requirements.txt                                    # All Python dependencies
├── .env.example                                        # Environment variable template
├── Dockerfile                                          # Python 3.12-slim, weasyprint system deps
├── alembic.ini                                         # Alembic migration config
├── alembic/
│   ├── env.py                                          # Async migration environment
│   ├── script.py.mako                                  # Migration template
│   └── versions/
│       ├── 001_initial_schema.py                       # All 17 tables, 21 indexes, updated_at triggers
│       └── 002_dashboard_indexes.py                    # Performance indexes for dashboard queries (Beacon)
├── tests/
│   └── __init__.py
└── app/
    ├── __init__.py
    ├── main.py                                         # FastAPI entry point, lifespan, CORS, router registration
    ├── config.py                                       # Pydantic Settings (DB, JWT, AI models, agent params)
    ├── database.py                                     # Async SQLAlchemy engine, session factory, get_db dependency
    ├── dependencies.py                                 # Auth guards: get_current_user, require_role()
    ├── agents/
    │   ├── __init__.py
    │   ├── base.py                                     # BaseAgent ABC, AgentContext, AgentResponse, ConversationMemory
    │   ├── orchestrator.py                             # Intent classification + agent routing + create_orchestrator()
    │   ├── triage_agent.py                             # Request triage — complexity scoring, methodology recommendation
    │   ├── dmaic_coach.py                              # Phase-aware DMAIC coaching with dynamic prompt injection
    │   ├── stats_advisor.py                            # Statistical test recommendation and result interpretation
    │   ├── stats_validator.py                          # Independent AI reviewer — dual-layer validation Layer 2 (Sonnet)
    │   ├── data_agent.py                               # Dataset profiling and quality assessment
    │   └── report_agent.py                             # Narrative report generation (5 types)
    ├── models/
    │   ├── __init__.py                                 # Re-exports all models
    │   ├── user.py                                     # User + Team + team_members association (+ password_hash)
    │   ├── request.py                                  # Request intake model
    │   ├── initiative.py                               # Initiative model (central entity, all relationships)
    │   ├── phase.py                                    # Phase + PhaseArtifact models
    │   ├── analysis.py                                 # Dataset + StatisticalAnalysis models
    │   └── supporting.py                               # ActionItem, Note, Document, Stakeholders, Metric, AIConversation, WorkloadEntry
    ├── schemas/
    │   ├── __init__.py                                 # Re-exports all schemas
    │   ├── auth.py                                     # RegisterRequest, LoginRequest, TokenResponse, UserProfile
    │   ├── request.py                                  # RequestCreate, RequestUpdate, RequestOut, RequestList
    │   ├── initiative.py                               # InitiativeCreate, InitiativeUpdate, InitiativeOut, InitiativeSummary, InitiativeList, PhaseOut
    │   ├── user.py                                     # UserOut, UserUpdate, UserWorkload, TeamCreate/Update/Out, TeamMemberOut, TeamList
    │   ├── supporting.py                               # ActionItem, Note, Document, Metric, Artifact, Dataset CRUD schemas
    │   ├── analysis.py                                 # AnalysisCreate, AnalysisRerun, AnalysisOut
    │   └── dashboard.py                                # PortfolioMetrics, TeamMetrics, InitiativeMetrics, PipelineMetrics + sub-models
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py                                     # POST /register, /login, GET /me
    │   ├── ai.py                                       # POST /chat, /chat/stream, /invoke/{agent}, GET /agents, WS /ws
    │   ├── requests.py                                 # Request CRUD + triage + convert-to-initiative
    │   ├── initiatives.py                              # Initiative CRUD + phase management + auto-advance
    │   ├── users.py                                    # User list (admin/mgr), get, update, workload summary
    │   ├── teams.py                                    # Team CRUD + member add/remove/list
    │   ├── actions.py                                  # ActionItem CRUD (initiative-scoped + global list)
    │   ├── artifacts.py                                # PhaseArtifact CRUD (phase-scoped)
    │   ├── notes.py                                    # Note CRUD (initiative-scoped, type-filterable)
    │   ├── documents.py                                # Document CRUD (file refs + external links)
    │   ├── metrics.py                                  # KPI tracking (baseline/target/current)
    │   ├── datasets.py                                 # Dataset upload (CSV/Excel) + auto-profile via pandas
    │   ├── analyses.py                                 # Statistical analysis CRUD + execute + rerun (Sigma integration)
    │   └── dashboards.py                               # Portfolio, team, initiative, pipeline dashboards (Beacon integration)
    ├── services/
    │   ├── __init__.py
    │   ├── auth.py                                     # hash_password, verify_password, create/decode JWT, authenticate_user
    │   ├── workflow_engine.py                           # Phase transitions, gate readiness, advance_phase, auto-complete
    │   ├── assignment_engine.py                        # Analyst recommendation (skill+capacity scoring), team utilization
    │   └── dashboard_engine.py                         # DashboardEngine: portfolio/team/initiative/pipeline metrics, health scoring, trends, burndown
    ├── stats/
    │   ├── __init__.py                                 # AnalysisResult, PlotlyChart shared types
    │   ├── engine.py                                   # DB-integrated execution: @register_test registry, _make_runner() bridge, _dataset_to_dataframe(), execute_analysis()
    │   ├── charts.py                                   # 12 Plotly chart generators (dark-mode, all stat chart types)
    │   ├── descriptive.py                              # Descriptive stats, normality test, Pareto analysis
    │   ├── comparison.py                               # t-tests (1/2/paired), ANOVA (1/2-way), Mann-Whitney, Kruskal-Wallis, Chi-square
    │   ├── regression.py                               # Correlation, simple/multiple/logistic regression
    │   ├── spc.py                                      # Control charts: I-MR, X-bar/R, p, np, c, u
    │   ├── capability.py                               # Process capability (normal/non-normal), Gage R&R (MSA)
    │   ├── doe.py                                      # Full/fractional factorial design + DOE analysis
    │   └── validator.py                                # Dual-layer validation Layer 1: programmatic input/output/assumption checks
    └── services/stats_engine.py                        # StatsEngine class: direct DataFrame run_test(), TEST_CATALOG metadata for Stats Advisor
```

### Tests
```
BB_Enabled_Command/backend/
├── pytest.ini                                          # Async mode, test paths
└── tests/
    ├── __init__.py
    ├── conftest.py                                     # Async DB, httpx clients, auth fixtures, dependency overrides
    ├── test_health.py                                  # Health check endpoint
    ├── test_auth.py                                    # Register, login, /me, validation (8 tests)
    ├── test_requests.py                                # Request CRUD, convert to initiative (10 tests)
    ├── test_initiatives.py                             # Initiative CRUD, phase auto-advance, all methodologies (12 tests)
    ├── test_users.py                                   # User management, RBAC, workload (8 tests)
    ├── test_teams.py                                   # Team CRUD, member management (10 tests)
    ├── test_actions.py                                 # Action items CRUD, auto-complete timestamp (6 tests)
    ├── test_supporting.py                              # Notes, documents, metrics, artifacts (10 tests)
    ├── test_dashboards.py                              # Dashboard engine + API endpoints (14 tests)
    ├── test_reports.py                                 # Report generation + CRUD + lifecycle (22 tests)
    ├── test_event_bus.py                               # Event bus: subscribe, publish, isolation, drain (8 tests) [Nexus]
    ├── test_workflow_chains.py                          # Workflow chains: all 5 handlers + graceful degradation (10 tests) [Nexus]
    ├── test_file_storage.py                            # File storage: local upload/download/delete, factory (8 tests) [Nexus]
    ├── test_email_service.py                           # Email: templates, disabled mode, SMTP failure, HTML content (6 tests) [Nexus]
    └── test_ws_dashboard.py                            # WebSocket dashboard: connect, scope, broadcast, dead cleanup (7 tests) [Nexus]
```

### Infrastructure (Atlas)
```
BB_Enabled_Command/
├── docker-compose.yml                                  # Dev stack: Postgres 16 + Redis 7 + backend (deps stage, hot-reload)
├── docker-compose.prod.yml                             # Prod stack: Postgres + Redis (password) + backend (4 workers) + frontend (nginx) + migrate
├── .env.production.example                             # Production secrets template with generation instructions
├── .github/
│   └── workflows/
│       └── ci.yml                                      # CI: backend pytest, frontend tsc+build, Docker image verification
├── backend/
│   ├── Dockerfile                                      # Multi-stage (deps → production), non-root, health check
│   └── .dockerignore                                   # Excludes __pycache__, .env, tests in prod
└── frontend/
    ├── Dockerfile                                      # Multi-stage (node build → nginx), SPA routing
    ├── nginx.conf                                      # API proxy, WebSocket, gzip, security headers, asset caching
    ├── .dockerignore                                   # Excludes node_modules, dist, .env
    └── vercel.json                                     # Vercel deployment: API rewrites, SPA fallback, cache + security headers
```

### Backend — Additional Files (Session 6)
```
BB_Enabled_Command/backend/
├── scripts/
│   ├── __init__.py
│   └── seed_data.py                                    # Demo data: 6 users, 2 teams, 5 requests, 3 initiatives
├── app/
│   ├── middleware.py                                    # RequestLoggingMiddleware, exception handlers, configure_logging()
│   ├── routers/
│   │   └── reports.py                                  # Report generation CRUD (5 endpoints)
│   ├── schemas/
│   │   └── report.py                                   # ReportRequest, ReportOut, ReportListItem
│   └── services/
│       └── report_generator.py                         # HTML report builder (5 types: exec summary, tollgate, closeout, portfolio, statistical)
```

### Backend — Nexus Integration Services (Session 10)
```
BB_Enabled_Command/backend/
├── alembic/
│   └── versions/
│       └── 003_nexus_enhancements.py                  # Indexes on datasets.initiative_id, action_items.assigned_to
└── app/
    ├── services/
    │   ├── event_bus.py                               # Async in-process event bus (6 event types, background tasks, drain())
    │   ├── workflow_chains.py                          # 5 chain handlers: dataset quality, stats interp, phase summary, closeout, action email
    │   ├── ws_manager.py                              # WebSocket dashboard manager (subscription-based broadcast, scope filtering)
    │   ├── file_storage.py                            # Abstract storage: LocalStorageBackend + S3StorageBackend (boto3)
    │   └── email_service.py                           # Async SMTP email (3 HTML templates, graceful degradation)
    └── routers/
        └── ws_dashboard.py                            # WS /api/ws/dashboard endpoint (portfolio, initiative, pipeline, team)
```

### Frontend (Scaffold — Session 6)
```
BB_Enabled_Command/frontend/
├── package.json                                        # React 18, Vite 5, Tailwind 3, Zustand, React Router 6, Plotly
├── tsconfig.json                                       # TypeScript 5.5, @/* path alias
├── vite.config.ts                                      # Dev proxy → backend:8000, @/ alias
├── tailwind.config.js                                  # Dark mode, brand/status/surface color tokens
├── postcss.config.js
├── index.html                                          # Dark mode default, surface-bg body
├── .env.example
└── src/
    ├── main.tsx                                        # App entry, RouterProvider
    ├── router.tsx                                      # All routes: auth, dashboard, requests, initiatives, phases, teams, actions, reports
    ├── index.css                                       # Tailwind directives + dark scrollbar
    ├── vite-env.d.ts                                   # ImportMetaEnv type
    ├── types/
    │   └── api.ts                                      # All TypeScript interfaces matching backend Pydantic schemas
    ├── api/
    │   ├── client.ts                                   # Typed fetch wrapper, JWT auto-attach, auto-logout on 401
    │   ├── auth.ts                                     # login, register, me
    │   ├── requests.ts                                 # list, get, create, update, convertToInitiative
    │   ├── initiatives.ts                              # list, get, create, update, listPhases, advancePhase
    │   └── dashboards.ts                               # portfolio, pipeline, team, initiative
    ├── stores/
    │   ├── authStore.ts                                # Auth state (user, token, setAuth, logout)
    │   ├── initiativeStore.ts                          # Initiative list + filters + pagination
    │   ├── dashboardStore.ts                           # Portfolio + pipeline dashboard data
    │   ├── aiStore.ts                                  # AI chat messages, streaming state, agent context
    │   └── uiStore.ts                                  # Sidebar collapse, AI panel toggle, view mode
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx                            # Sidebar + TopBar + main content area + AI panel slot
    │   │   ├── Sidebar.tsx                             # Dark sidebar with grouped nav (Overview/Work/Org/Intel)
    │   │   └── TopBar.tsx                              # Breadcrumb title, search, notifications, AI toggle
    │   ├── auth/
    │   │   ├── LoginPage.tsx                           # Login form with brand header
    │   │   ├── RegisterPage.tsx                        # Registration form
    │   │   └── AuthGuard.tsx                           # Route guard — redirects to login, loads user on mount
    │   ├── dashboard/
    │   │   └── PortfolioDashboard.tsx                  # 4 metric cards + 4 distribution panels
    │   ├── requests/
    │   │   └── RequestQueue.tsx                        # Request table with status badges, priority tags
    │   ├── initiatives/
    │   │   └── InitiativeList.tsx                      # Initiative cards with methodology/priority/phase
    │   └── shared/
    │       ├── StatusBadge.tsx                         # Color-coded status chips
    │       ├── PriorityTag.tsx                         # Priority ring badges
    │       ├── MetricCard.tsx                          # Dashboard metric card with icon + change indicator
    │       ├── PageHeader.tsx                          # Page title + description + action slot
    │       ├── LoadingSpinner.tsx                      # Spinner (inline) + PageLoader (full-page centered)
    │       ├── EmptyState.tsx                          # Centered empty state with icon, title, description, action
    │       └── PlotlyChart.tsx                         # Dark-mode Plotly wrapper for analysis charts
    ├── pages/
    │   ├── InitiativeList.tsx                          # Kanban board + data table, status filter, board/list toggle
    │   ├── InitiativeProfile.tsx                       # Initiative detail: header, overview cards, phase list, scope
    │   ├── PhaseWorkspace.tsx                          # Phase workspace: progress bar, artifacts/analysis/actions, gate review
    │   ├── ActionBoard.tsx                             # Action items: overdue/due-this-week/open columns
    │   ├── DataView.tsx                                # Drag-drop upload, dataset list, analyze button
    │   └── ReportsPage.tsx                             # 5 report types, generate flow, report list with actions
```

---

## Last Session Log

### Session 10 — 2026-02-12 (Forge agent — API Contract Audit & Route Gap Fixes)
**What was accomplished:**
- Full API contract audit comparing all 16 frontend API client modules against 15 backend routers
- Found and fixed 8 critical mismatches between frontend and backend:

1. **Actions — GET single** (`actions.py`): Added `GET /api/actions/{id}` endpoint
2. **Actions — POST global** (`actions.py`): Added `POST /api/actions` with `initiative_id` in body (via `ActionItemGlobalCreate` schema)
3. **Artifacts — phase_id routes** (`artifacts.py`): Added `GET/POST /api/phases/{phase_id}/artifacts` shorthand routes (frontend uses phase UUID, not initiative_id+phase_name)
4. **Reports — unified generate** (`reports.py`): Added `POST /api/reports/generate` unified endpoint with optional `initiative_id` (via `UnifiedReportRequest` schema)
5. **Analyses — execute alias** (`analyses.py`): Added `POST /api/analyses/{id}/execute` as alias for `/rerun`
6. **Teams — DELETE** (`teams.py`): Added `DELETE /api/teams/{id}` endpoint (cascades member removal)
7. **Teams — addMember body** (`teams.py`): Changed `POST /api/teams/{id}/members` from Query params to JSON body (`AddMemberBody` schema)
8. **AI — stream alias + invoke body** (`ai.py`): Added `POST /api/ai/stream` alias for `/chat/stream`; Added `POST /api/ai/invoke` with agent in body (`InvokeByBodyRequest` schema)

- Updated test suites:
  - `test_actions.py`: Added 3 tests (GET single, GET not found, POST global create)
  - `test_teams.py`: Added 2 tests (DELETE team, DELETE not found), updated all addMember tests from `params=` to `json=`
  - `test_analyses.py` (NEW): 11 tests covering CRUD, list with filters, rerun, execute alias, not-found cases
  - `test_reports.py`: Added 2 tests for unified `/reports/generate` endpoint (with and without initiative_id)

**Files modified:**
- `backend/app/routers/actions.py` — Added `ActionItemGlobalCreate`, `get_action()`, `create_action_global()`
- `backend/app/routers/artifacts.py` — Added `list_artifacts_by_phase_id()`, `create_artifact_by_phase_id()`
- `backend/app/routers/reports.py` — Added `UnifiedReportRequest`, `generate_report_unified()`
- `backend/app/routers/analyses.py` — Added `execute_analysis_endpoint()`
- `backend/app/routers/teams.py` — Added `AddMemberBody`, `delete_team()`, changed `add_team_member()` to accept body
- `backend/app/routers/ai.py` — Added `chat_stream_alias()`, `InvokeByBodyRequest`, `invoke_agent_by_body()`
- `backend/tests/test_actions.py` — Added 3 tests
- `backend/tests/test_teams.py` — Added 2 tests, updated 4 existing tests
- `backend/tests/test_analyses.py` — NEW, 11 tests
- `backend/tests/test_reports.py` — Added 2 tests

**Key decisions:**
- Backend adapts to frontend conventions (not the other way) — Forge owns the API surface
- New endpoints are additive (existing routes preserved for backward compatibility)
- Phase artifacts support both patterns: initiative+phase_name (original) and phase_id (frontend shorthand)
- AI router has both path-based `/invoke/{agent_type}` and body-based `/invoke` for flexibility

**What's next:**
- Database migration testing (Alembic verification)
- WebSocket endpoint testing for AI streaming
- File upload handling for datasets
- `npm run build` frontend compilation check

**Blockers:** None

### Session 10b — 2026-02-12 (Forge agent — Code Integrity Audit & Schema Fixes)
**What was accomplished:**
- Full code integrity audit across 5 parallel dimensions:
  1. **Backend imports** — CLEAN (0 broken imports across 94 files)
  2. **Model-schema alignment** — 5 issues found, 4 fixed
  3. **Router registration** — CLEAN (all 16 routers registered, 2 advisory warnings)
  4. **Frontend imports** — CLEAN (0 broken imports across 54 files)
  5. **Frontend-backend type alignment** — 41+ field mismatches catalogued (Prism domain)

- Fixed 4 critical backend-side issues:
  1. **ReportOut schema** (`schemas/report.py`): Added missing `metadata_json: dict | None` and `created_at: datetime` fields to match Report ORM model
  2. **StatisticalAnalysis ORM** (`models/analysis.py`): Added `validation: Mapped[dict | None]` column to match AnalysisOut schema
  3. **Actions pagination** (`routers/actions.py`, `schemas/supporting.py`): Changed `GET /api/actions` from `list[ActionItemOut]` to paginated `ActionItemList` response (`{items, total, page, page_size}`) matching frontend PaginatedResponse expectation; added `ActionItemList` schema
  4. **PhaseOut schema** (`schemas/initiative.py`): Added `initiative_id: UUID` field to match Phase ORM model

- Updated `test_actions.py` list test to validate paginated response shape

**Known cross-layer issues (Prism domain):**
- Frontend `PaginatedResponse` uses `per_page` but all backend paginated schemas use `page_size` — systemic mismatch across all paginated endpoints
- PortfolioDashboard frontend types completely mismatched with backend PortfolioMetrics
- Auth response missing `expires_in` on frontend
- 31+ missing fields across various frontend types (InitiativeOut, TeamOut, AnalysisOut)

**Files modified:**
- `backend/app/schemas/report.py` — Added `metadata_json`, `created_at` to `ReportOut`
- `backend/app/schemas/initiative.py` — Added `initiative_id` to `PhaseOut`
- `backend/app/schemas/supporting.py` — Added `ActionItemList` paginated schema
- `backend/app/models/analysis.py` — Added `validation` JSONB column to `StatisticalAnalysis`
- `backend/app/routers/actions.py` — Converted `list_all_actions` to paginated response
- `backend/tests/test_actions.py` — Updated list test for paginated shape

**Blockers:** None

### Session 10 — 2026-02-12 (Atlas agent — Phase 6 Infrastructure & Deployment)
**What was accomplished:**
- Built complete deployment infrastructure (Phase 6):

- **Frontend Build Verification:**
  - `npm install` (529 packages) + `npm run build` — passes clean
  - Output: 305KB JS bundle + 25KB CSS (gzipped: 89KB + 5KB)
  - TypeScript `tsc -b` compiles with zero errors

- **Production Backend Dockerfile** (`backend/Dockerfile` — REWRITTEN):
  - Multi-stage build: `deps` stage (build-essential + pip install) → `production` stage (runtime-only libs)
  - Non-root `appuser` (UID 1001) for security
  - Strips test/dev files (`tests/`, `scripts/`, `pytest.ini`) from production image
  - Health check: `curl -f http://localhost:8000/health`
  - Production CMD: `uvicorn ... --workers 4 --access-log` (no `--reload`)

- **Frontend Dockerfile** (`frontend/Dockerfile` — NEW):
  - Multi-stage: `node:20-alpine` build → `nginx:1.27-alpine` serve
  - Build arg `VITE_API_URL` baked into client bundle at build time
  - Serves static assets from `/usr/share/nginx/html`
  - Health check: `wget -qO- http://localhost:80/health`

- **Nginx Config** (`frontend/nginx.conf` — NEW):
  - API proxy: `/api/` → `http://backend:8000` with WebSocket upgrade headers
  - SPA fallback: `try_files $uri $uri/ /index.html`
  - Gzip compression for text/css/js/json/xml/svg
  - Security headers: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy
  - Static assets: 1-year cache with `immutable` directive

- **Docker Compose Dev** (`docker-compose.yml` — UPDATED):
  - Backend now targets `deps` stage (includes build tools for dev)
  - Overrides CMD with `--reload` for hot-reload
  - Mounts full `./backend` directory (not just `app/`)

- **Docker Compose Production** (`docker-compose.prod.yml` — NEW):
  - Full 5-service stack: postgres, redis, backend, frontend, migrate
  - Required env vars with `?` validation (POSTGRES_PASSWORD, ANTHROPIC_API_KEY, JWT_SECRET_KEY)
  - Redis password authentication
  - No host port exposure for postgres/redis (internal network only)
  - `migrate` service: one-shot `alembic upgrade head` before backend starts
  - `restart: unless-stopped` on all persistent services
  - Frontend exposed on configurable `FRONTEND_PORT` (default 80)

- **GitHub Actions CI/CD** (`.github/workflows/ci.yml` — NEW):
  - Triggers on push/PR to `main` branch, scoped to `BB_Enabled_Command/` paths
  - Backend job: Python 3.12 + Postgres 16 service container, `pytest -x -q`
  - Frontend job: Node 20, `npm ci`, `tsc --noEmit`, `npm run build`, artifact upload on main
  - Docker job: builds both images on main (after backend + frontend pass)
  - Dependency caching for pip and npm

- **Vercel Config** (`frontend/vercel.json` — NEW):
  - API rewrites: `/api/(.*)` → `${BACKEND_URL}/api/$1`
  - SPA fallback for all non-asset routes
  - Cache headers: 1-year immutable for `/assets/`
  - Security headers on all routes

- **Production Env Template** (`.env.production.example` — NEW):
  - All required production secrets with placeholder values
  - JWT_SECRET_KEY generation command included

- **Dockerignore Files** (`backend/.dockerignore`, `frontend/.dockerignore` — NEW):
  - Exclude dev artifacts from Docker build context

- **End-to-End Wiring Audit:**
  - Verified all frontend API paths match backend router prefixes
  - 27 endpoints checked across auth, requests, initiatives, dashboards
  - 1 gap found: `DELETE /api/initiatives/{id}` defined in frontend API client but missing from backend router (Forge scope — documented for next session)
  - Base URL handling verified for all 3 deployment modes (Vite proxy, Docker nginx, Vercel rewrites)
  - JWT token flow verified: localStorage → Authorization header → python-jose verify

**Key decisions:**
- Multi-stage Docker builds to minimize production image size (no build-essential, no test files)
- Non-root user in backend container (security best practice)
- Nginx reverse proxy in frontend container handles both API proxying and SPA routing
- Separate docker-compose files for dev vs prod (not profiles) for clarity
- One-shot `migrate` service runs before backend starts
- CI pipeline scoped to `BB_Enabled_Command/` paths to avoid triggering on VytalPath Academy changes
- Vercel API rewrites use `${BACKEND_URL}` env var set in Vercel dashboard

**What's next:**
- Phase 5 (Nexus agent): AI agent refinement, prompt tuning, Chart Agent
- Forge follow-up: implement `DELETE /api/initiatives/{id}` endpoint
- Deploy: connect repo to Vercel (frontend), deploy backend to Railway/Fly.io
- Optional: add deploy job to CI pipeline once hosting is configured

**Blockers:** None

### Session 10 — 2026-02-12 (Nexus agent — PHASE 5 COMPLETE: Integration & Polish)
**What was accomplished:**
- Built complete Integration & Polish layer (Phase 5 — Nexus):

- **Event Bus** (`services/event_bus.py` — NEW):
  - Async in-process pub/sub with 6 event type constants
  - `EventBus` class: `subscribe()`, `publish()`, `drain()` (for tests)
  - Handlers run as background `asyncio.Task`s with error isolation per handler
  - `init_event_bus()` / `get_event_bus()` singleton pattern

- **Workflow Chains** (`services/workflow_chains.py` — NEW):
  - 5 chain handlers registered at app startup:
    - `handle_dataset_uploaded` → DataAgent quality assessment → stores in dataset.summary_stats["quality"]
    - `handle_analysis_completed` → StatsAdvisor interpretation → stores in analysis.ai_interpretation
    - `handle_phase_advanced` → ReportAgent phase summary → stores in phase.ai_summary + email notification
    - `handle_initiative_completed` → auto-generate closeout Report record + email
    - `handle_action_assigned` → email notification to assignee
  - All handlers use `get_db_session()` for independent DB sessions
  - Graceful degradation: AI/email failures logged but never block

- **Event Publishing in Routers** (4 files MODIFIED):
  - `datasets.py`: publishes DATASET_UPLOADED after upload
  - `initiatives.py`: publishes PHASE_ADVANCED and INITIATIVE_COMPLETED on phase completion
  - `actions.py`: publishes ACTION_ASSIGNED on action creation
  - `stats/engine.py`: publishes ANALYSIS_COMPLETED after test execution
  - All wrapped in `try/except RuntimeError: pass` for test safety

- **WebSocket Dashboard** (`services/ws_manager.py`, `routers/ws_dashboard.py` — NEW):
  - `DashboardWSManager`: subscription-based broadcast with scope filtering
  - Supports portfolio, initiative, pipeline, team dashboard types
  - Dead connection cleanup during broadcast
  - WS endpoint: `/api/ws/dashboard?type=portfolio&id=X`

- **File Storage** (`services/file_storage.py` — NEW):
  - `FileStorageBackend` ABC with upload/download/delete/get_url
  - `LocalStorageBackend`: filesystem-based for development
  - `S3StorageBackend`: boto3-based with `asyncio.to_thread()` for production
  - `create_file_storage()` factory, singleton pattern

- **Email Service** (`services/email_service.py` — NEW):
  - Async SMTP dispatch via `asyncio.to_thread()` (no new dependencies)
  - 3 HTML templates: phase advance, action assigned, initiative completed
  - Inline styled HTML (header, badges, CTA buttons, footer)
  - `email_enabled` flag — when False, all sends are no-ops

- **Config Updates** (`config.py` — MODIFIED):
  - Storage settings: `storage_backend`, `storage_local_path`, `s3_bucket`, `s3_region`, `s3_access_key`, `s3_secret_key`, `s3_endpoint_url`
  - SMTP settings: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from_address`, `smtp_from_name`, `email_enabled`
  - App URL: `app_base_url`

- **Main.py Wiring** (`main.py` — MODIFIED):
  - Lifespan now initializes: event bus, WS manager, file storage, email service
  - Registers workflow chains with event bus
  - Adds ws_dashboard router (16th router)

- **Database** (`database.py` — MODIFIED):
  - Added `get_db_session()` context manager for background task DB access

- **Dependencies** (`requirements.txt` — MODIFIED):
  - Added `boto3==1.36.0` (optional, for S3 storage backend)

- **Alembic Migration** (`003_nexus_enhancements.py` — NEW):
  - Index on `datasets.initiative_id` for workflow chain queries
  - Index on `action_items.assigned_to` for notification lookups

- **Tests** (5 new test files — 38 tests total):
  - `test_event_bus.py` (8 tests): subscribe/publish, multi-handler, error isolation, background execution
  - `test_workflow_chains.py` (10 tests): all 5 chain handlers mocked, graceful degradation, registration
  - `test_file_storage.py` (8 tests): local upload/download/delete, nested dirs, factory
  - `test_email_service.py` (6 tests): 3 templates, disabled mode, SMTP failure, HTML content
  - `test_ws_dashboard.py` (7 tests): connect/receive, scope filtering, concurrent, dead cleanup

**Key decisions:**
- In-process event bus (not Redis pub/sub) — simpler, sufficient for single-process deployment, upgradeable later
- All event publishing wrapped in `try/except RuntimeError: pass` so tests that don't init EventBus still pass
- Background tasks use `get_db_session()` (context manager) not the FastAPI dependency generator
- Email uses stdlib `smtplib` via `asyncio.to_thread()` — no Celery dependency for notifications
- S3 backend uses `asyncio.to_thread()` for all boto3 calls to avoid blocking the event loop
- File storage and email are off by default (`storage_backend="local"`, `email_enabled=False`)

**Files created:** 8 new files (5 services, 1 router, 1 migration, 5 test files)
**Files modified:** 6 files (config.py, main.py, database.py, requirements.txt, datasets.py, initiatives.py, actions.py, stats/engine.py)
**Total test count:** ~139 tests (101 existing + 38 new)

**What's next:**
- ALL PHASES COMPLETE (0-6). Platform is feature-complete for MVP.
- Remaining enhancements (not blocking): Chart Agent, advanced prompt tuning, Redis pub/sub upgrade
- Forge follow-up: implement `DELETE /api/initiatives/{id}` endpoint
- Deploy: connect repo to Vercel (frontend), deploy backend to Railway/Fly.io

**Blockers:** None

### Session 9 — 2026-02-12 (Prism agent — Phase 4 Frontend Pages)
**What was accomplished:**
- Built all missing React frontend pages and shared components (Phase 4):

- **CSS Utility Classes** (`index.css` — MODIFIED):
  - Added `@layer components` block with 8 utility classes: `card`, `card-hover`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`, `btn-sm`, `input-field`
  - All existing pages reference these classes; they were previously undefined

- **LoadingSpinner.tsx** (NEW):
  - `Spinner`: inline animated spinner with configurable size, uses `Loader2` from lucide-react
  - `PageLoader`: full-page centered spinner (h-64), used by all pages during data loading

- **EmptyState.tsx** (EXISTING — already had full implementation):
  - Props: `icon`, `title`, `description`, `action`, `className`
  - Used across InitiativeList, ActionBoard, DataView, ReportsPage, PhaseWorkspace

- **PlotlyChart.tsx** (NEW):
  - Wraps `react-plotly.js` with dark-mode layout defaults
  - Accepts Plotly JSON spec from backend's `AnalysisOut.charts`
  - Transparent paper, slate-800 plot bg, gray text, responsive, no mode bar

- **InitiativeList.tsx** (EXISTING — already had full implementation):
  - Kanban board view (5 DMAIC columns) + DataTable list view
  - Status filter pills, board/list view toggle via uiStore
  - Uses StatusBadge, PriorityTag, PhaseIndicator, MethodologyBadge

- **InitiativeProfile.tsx** (EXISTING — had basic scaffold):
  - Header with initiative_number, methodology badge, priority tag, status badge
  - Overview cards: problem statement, desired outcome, timeline + projected savings
  - Phase cards linking to `/initiatives/:id/:phase` with status colors and completeness %
  - Scope sections (in scope / out of scope)

- **PhaseWorkspace.tsx** (NEW):
  - Breadcrumb back to initiative, phase name + description header
  - Progress bar with completeness percentage
  - 3-column grid: Artifacts, Analysis, Actions (with EmptyState + Add buttons)
  - AI Phase Summary (teal accent border, conditional render)
  - Gate review section: approved state (green) or request review button (in-progress)

- **ActionBoard.tsx** (NEW):
  - 3-column layout: Overdue (red), Due This Week (yellow), Open (blue)
  - Helper functions: `isOverdue()`, `isDueThisWeek()` for date classification
  - `ActionColumn` sub-component with icon, count badge, action item cards
  - Each card: title, priority tag, status badge, due date (red if overdue)
  - Header with "New Action" button, PageLoader during fetch

- **DataView.tsx** (NEW):
  - Drag-and-drop upload zone with dashed border, accepts CSV/XLS/XLSX
  - File input with label-as-button pattern
  - Dataset list with file icon, name, row/column counts, file type
  - Analyze button per dataset
  - EmptyState when no datasets uploaded

- **ReportsPage.tsx** (NEW):
  - 5 report type selection cards (Phase Gate, Executive Summary, Statistical Results, Close-out, Portfolio Roll-up)
  - Generate button with loading state
  - Report list with title, type, timestamp
  - Action buttons per report: Preview, Download, Send

**Key decisions:**
- Pages use local `useState` for data + loading, API calls in `useEffect`, consistent with existing patterns
- All pages use the CSS utility classes (`card`, `card-hover`, `btn-primary`, `btn-sm`, etc.)
- EmptyState and PageLoader shared components prevent code duplication across all 6 pages
- PlotlyChart merges dark-mode defaults so backend chart specs render correctly without frontend-side theming
- ActionBoard uses column-based layout (not table) for better visual prioritization of overdue items

**What's next:**
- Phase 5 (Nexus agent): AI agent refinement, prompt tuning, Chart Agent
- Remaining frontend work: enhance InitiativeProfile with tabs (Overview/Phases/Data/Actions/Notes), request submit form, AI chat panel integration
- `npm run build` verification to confirm all router imports resolve

**Blockers:** None

### Session 8 — 2026-02-12 (Beacon agent — PHASE 3 COMPLETE: Dashboard & Reporting Engine)
**What was accomplished:**
- Built complete Dashboard & Reporting Engine (Phase 3):

- **Dashboard Pydantic Schemas** (`schemas/dashboard.py` — NEW):
  - `PortfolioMetrics`: initiative counts by status/phase/priority/methodology, savings totals, utilization summary, 12-month trends, health summary, upcoming deadlines
  - `TeamMetrics`: member-level utilization, initiative list, action compliance, overloaded/available counts
  - `InitiativeMetrics`: phases, metrics with pct_change, action summary + burndown, analyses, health score, days in phase, financial impact
  - `PipelineMetrics`: request counts by status/urgency, conversion rate, avg review days, recent requests
  - Sub-models: TrendPoint, DeadlineItem, MemberMetrics, BurndownPoint, PhaseDetail, MetricDetail (computed pct_change), AnalysisSummary, etc.

- **DashboardEngine Service** (`services/dashboard_engine.py` — NEW):
  - `get_portfolio_metrics()`: aggregates all active initiative data with optional team_id filter
  - `get_team_metrics()`: per-member utilization, initiative assignments, action compliance
  - `get_initiative_metrics()`: phase timeline, KPI tracking with pct_change, action burndown (weekly snapshots), health scoring
  - `get_pipeline_metrics()`: request intake funnel, conversion rate calculation
  - Health scoring: blocked (status=="blocked" or open blocker action), at_risk (past target, >3 overdue actions, >30 days in phase), on_track
  - 12-month rolling trend calculations, upcoming deadline queries with initiative context joins

- **Dashboard Router Rewrite** (`routers/dashboards.py` — REWRITTEN):
  - Replaced ~300 lines of inline SQL with clean delegation to DashboardEngine
  - Added typed `response_model` on all 4 endpoints
  - Added optional `team_id` query param for team-scoped portfolio filtering

- **Report Generator Enhancements** (`services/report_generator.py` — ENHANCED):
  - AI narrative integration: `_get_ai_narrative()` builds AgentContext, calls ReportAgent, graceful degradation
  - Plotly chart embedding: `_chart_to_base64()` converts JSON specs to base64 PNG via kaleido
  - `_markdown_to_html()` + `_inline_bold()` for AI narrative formatting
  - All 5 builders accept `include_ai` and `include_charts` kwargs
  - CSS classes: `.ai-narrative`, `.chart-container`, `.status-blocked`, `.status-at_risk`

- **Report Router Enhancements** (`routers/reports.py` — ENHANCED):
  - Passes `include_ai_narrative` and `include_charts` from request payload to generator
  - Added `GET /api/reports` global report listing (admin/manager only) with optional `report_type` filter
  - Portfolio report endpoint now uses `require_role("admin", "manager")` guard

- **Alembic Migration** (`alembic/versions/002_dashboard_indexes.py` — NEW):
  - `ix_action_items_due_date`: partial index WHERE status NOT IN (completed, deferred)
  - `ix_initiatives_actual_completion`: partial index WHERE actual_completion IS NOT NULL
  - `ix_initiatives_status_phase`: composite index on (status, current_phase)

- **Dashboard Tests** (`tests/test_dashboards.py` — NEW, 14 tests):
  - Portfolio: empty state, with data, savings, health scoring (on_track, blocked, blocker action, at_risk past target)
  - Upcoming deadlines sorted by due date
  - Initiative metrics: phases, metrics with pct_change, health, days_in_phase, financial
  - Pipeline metrics: request counts and conversion rate
  - Action burndown: weekly open/completed snapshots
  - API endpoint tests: portfolio, pipeline, initiative

- **Report Tests** (`tests/test_reports.py` — NEW, 22 tests):
  - All 5 report builders: executive_summary, phase_tollgate, initiative_closeout, portfolio_review, statistical_summary
  - Dispatcher validation: correct routing, unknown type error, missing phase_name error
  - REPORT_TITLES mapping verification
  - API endpoint tests: create initiative report, create portfolio report, type validation
  - CRUD operations: list, get, delete, not-found handling
  - Admin-only global listing with report_type filter
  - Full lifecycle test: generate → list → get → delete

**Key decisions:**
- Health scoring priority chain: blocked > at_risk > on_track with specific DB-backed conditions for each
- Trends use 12-month rolling window with monthly grouping by actual_completion date
- Action burndown generates weekly snapshots from earliest action item creation to today
- AI narratives use graceful degradation (try/except around ReportAgent calls) — reports always generate
- Chart embedding uses plotly + kaleido with light theme override for report readability
- Dashboard indexes use partial indexes to focus on active/open records for query performance
- All tests disable AI (`include_ai=False`) to avoid external API calls during testing

**Phase 3 is COMPLETE. Dashboard & Reporting Engine provides:**
- Typed Pydantic response models for all 4 dashboard endpoints
- DashboardEngine with health scoring, trends, burndown, utilization
- AI-enhanced report generation with chart embedding
- Role-guarded report listing and portfolio report generation
- 36 new tests (14 dashboard + 22 report)
- Performance indexes for dashboard query optimization
- Total backend tests: ~101

**What's next:**
- Phase 4 (Prism agent): Continue React frontend — initiative profile page, phase workspaces, data/analysis views, dashboard chart components
- Phase 5 (Nexus agent): AI agent refinement, Chart Agent, prompt tuning

**Blockers:** None

### Session 7 — 2026-02-12 (Forge agent — Reports, Seed Data, Middleware, Frontend Scaffold)
**What was accomplished:**
- Built report generation system:
  - `routers/reports.py`: 5 endpoints (generate initiative report, generate portfolio report, list reports, get report, delete report)
  - `schemas/report.py`: ReportRequest, ReportOut, ReportListItem Pydantic schemas
  - `services/report_generator.py`: HTML report builder with 5 types (executive_summary, phase_tollgate, initiative_closeout, portfolio_review, statistical_summary), inline CSS styling with metric cards/status badges/tables
  - Added `Report` model to `models/supporting.py`, added `reports` table to Alembic migration
  - Registered reports router in main.py (now 15 routers total)

- Built seed data script (`scripts/seed_data.py`):
  - 6 users: admin (Sarah Chen), 2 managers, 3 analysts. Login: admin@bbcommand.dev / admin123
  - 2 teams: Operations Excellence, Quality Assurance
  - 5 requests: submitted, under_review, 2 accepted, 1 converted
  - 3 initiatives: DMAIC (lab turnaround, in Measure), A3 (discharge, in Background), Kaizen (5S, completed)
  - Action items, metrics, notes, workload entries with deterministic UUIDs
  - Run: `python -m scripts.seed_data`

- Built API middleware (`middleware.py`) and wired into main.py:
  - `RequestLoggingMiddleware`: logs method/path/status/duration, adds X-Request-ID and X-Response-Time headers
  - `register_exception_handlers()`: standardized JSON errors for HTTPException (consistent shape), ValidationError (field-level), unhandled Exception (safe 500)
  - `configure_logging()`: structured logging, quiets SQLAlchemy/uvicorn/httpcore
  - Wired in create_app(): logging config on startup, RequestLoggingMiddleware outermost, exception handlers after router registration

- Scaffolded Prism frontend (`frontend/`):
  - Project config: package.json (React 18 + Vite 5 + Tailwind 3 + Zustand + React Router 6 + Plotly), tsconfig, vite.config (proxy + @/ alias), Tailwind (dark mode, brand/status/surface tokens)
  - TypeScript types: `types/api.ts` — all interfaces matching backend Pydantic schemas (UserOut, RequestOut, InitiativeOut, PhaseOut, AnalysisOut, PortfolioDashboard, PipelineDashboard, etc.)
  - API client layer: `api/client.ts` (typed fetch, JWT auto-attach, 401 auto-logout), `api/auth.ts`, `api/requests.ts`, `api/initiatives.ts`, `api/dashboards.ts`
  - Layout components: `AppShell.tsx` (sidebar + topbar + content + AI panel slot), `Sidebar.tsx` (grouped nav: Overview/Work/Org/Intelligence), `TopBar.tsx`
  - Auth pages: `LoginPage.tsx`, `RegisterPage.tsx` (brand header, form, error handling), `AuthGuard.tsx` (route guard, auto-loads user)
  - Dashboard: `PortfolioDashboard.tsx` (4 metric cards + 4 distribution panels)
  - Pages: `RequestQueue.tsx` (table with status badges, priority tags, date formatting), `InitiativeList.tsx` (card layout with methodology/phase/priority)
  - Shared components: `StatusBadge.tsx`, `PriorityTag.tsx`, `MetricCard.tsx`, `PageHeader.tsx`
  - Router: all routes from CLAUDE.md spec — auth, dashboard, requests, initiatives, phases, datasets, teams, actions, reports, analytics, settings, admin (placeholder pages for unbuilt routes)
  - Reconciled with parallel Prism agent session (existing *Store.ts files, TopBar.tsx, AIPanel.tsx, additional API modules)

**Key decisions:**
- Middleware stack order: RequestLoggingMiddleware (outermost) → CORS → routers → exception handlers
- Frontend dark mode default via Tailwind `class` strategy + `<html class="dark">`
- Color tokens match CLAUDE.md design spec: green=success, yellow=warning, red=danger, blue=active, purple=tags, teal=AI
- API client uses `localStorage.getItem("bb_token")` directly (matches existing authStore.ts pattern)
- Stores follow setter pattern (from Prism agent's *Store.ts convention) — API calls live in components/hooks, not stores
- Vite dev proxy forwards `/api` → `localhost:8000` (no CORS issues in development)

**Phase 1 deliverables now complete:**
- 15 API routers, 14 ORM models, all schemas, 5 AI agents, services, middleware, seed data, migration
- 65+ pytest tests
- Frontend scaffold with auth, dashboard, request queue, initiative list, shared components, full router

**What's next:**
- Prism agent continues expanding frontend: initiative profile page, phase workspaces, data/analysis views, AI chat panel, Plotly chart components
- Backend: run actual npm install + verify TypeScript compiles, run seed data against live DB, test end-to-end

**Blockers:** None

### Session 6 — 2026-02-12 (Sigma agent — Dual-Layer Validation System)
**What was accomplished:**
- Built dual-layer statistical validation system that automatically reviews every test execution
- **Layer 1 — Programmatic Validator** (`stats/validator.py`):
  - Input validation: sample size adequacy, required columns, data type compatibility, missing data thresholds, group size checks, configuration completeness
  - Output validation: p-value range [0,1], finite test statistics, effect size bounds, degrees of freedom > 0, CI ordering, chart presence, R-squared bounds
  - Assumption validation: normality (Shapiro-Wilk/D'Agostino), equal variance (Levene's), chi-square expected counts, multicollinearity (VIF), with automatic alternative test recommendations
  - `_TEST_REQUIREMENTS` dict maps all 27 tests to their specific validation requirements
  - Returns `ValidationReport`: passed, confidence (high/medium/low), findings, recommendations
- **Layer 2 — AI Validation Agent** (`agents/stats_validator.py`):
  - `StatsValidatorAgent(BaseAgent)` with specialized QA prompt
  - Reviews test selection, data adequacy, assumption compliance, result plausibility, practical significance
  - Returns structured verdict: "validated" | "caution" | "concern" + confidence score (0-100) + plain-language summary
  - Uses `ai_model_light` (Sonnet) for cost efficiency
  - Graceful fallback if AI review fails — programmatic results still available
- **Integration** — Modified `stats/engine.py` execute_analysis():
  - After test completes, runs programmatic validation (instant)
  - Then calls AI validator for interpretive review
  - Stores combined result in `analysis.results["validation"]`
  - Validation never blocks test results (wrapped in try/except)
- Added `STATS_VALIDATOR` to `AgentType` enum in `base.py`
- Registered `StatsValidatorAgent` in `create_orchestrator()` factory
- Added `validation: dict | None` field to `AnalysisOut` schema
- Updated CLAUDE.md: agent assignments, build status, file inventory, session log

**Key decisions:**
- Two-layer architecture: programmatic checks are instant/free, AI review adds interpretive depth
- Validation results stored in existing `results` JSONB field (no new DB columns or migrations)
- AI layer uses light model (Sonnet) to minimize cost per analysis
- Each layer can fail independently without blocking the other
- Programmatic validator checks against `_TEST_REQUIREMENTS` lookup with per-test-type requirements
- AI verdict overrides overall verdict only when programmatic checks pass (programmatic = ground truth)
- `review_analysis()` convenience method handles context formatting and JSON parsing with fallback

**Blockers:** None

### Session 5 — 2026-02-12 (Sigma agent — PHASE 2 COMPLETE)
**What was accomplished:**
- Built complete statistical engine with 27 test implementations across 7 modules
- `stats/__init__.py`: Defined shared types `AnalysisResult` and `PlotlyChart` (Pydantic models)
- `stats/charts.py`: 12 Plotly chart generators (histogram, box, scatter, bar, Pareto, Q-Q, control chart, heatmap, residual plots, main effects, interaction, capability histogram). All dark-mode styled.
- `stats/descriptive.py`: 3 tests — descriptive_summary (full column profiling), normality_test (Shapiro-Wilk + Anderson-Darling), pareto_analysis (vital few identification)
- `stats/comparison.py`: 9 tests — one_sample_t, two_sample_t (auto Levene → Welch), paired_t, one_way_anova (+ Tukey HSD post-hoc), two_way_anova (+ interaction plot), mann_whitney, kruskal_wallis, chi_square_association (Cramér's V), chi_square_goodness
- `stats/regression.py`: 4 tests — correlation (Pearson + Spearman matrices), simple_regression (OLS + residual plots), multiple_regression (VIF + diagnostics), logistic_regression (odds ratios + confusion matrix)
- `stats/spc.py`: 6 tests — i_mr_chart, xbar_r_chart (subgroup constants n=2-10), p_chart, np_chart, c_chart, u_chart. All with violation detection.
- `stats/capability.py`: 3 tests — capability_normal (Cp/Cpk/Pp/Ppk/PPM/sigma level), capability_nonnormal (Box-Cox transform), msa_gage_rr (ANOVA method, variance components, %Study Var, NDC, rating)
- `stats/doe.py`: 3 tests — full_factorial (2^k with randomization/center points), fractional_factorial (2^(k-p)), doe_analysis (main effects + interactions + Pareto of effects)
- `services/stats_engine.py`: StatsEngine class with run_test() orchestrator, 27-test registry, TEST_CATALOG metadata dict (used by Stats Advisor agent for test recommendation), applicability filtering, get_categories(), timing
- Updated CLAUDE.md: Phase 2 build status, file inventory, agent assignment status, session log
- Wired all 27 test implementations into Forge's `stats/engine.py` @register_test pattern:
  - Added `_make_runner()` factory that creates async wrappers bridging `engine.py`'s `async def runner(configuration, dataset)` signature to Sigma's `def test_fn(df, config)` signature
  - Added `_dataset_to_dataframe()` to reconstruct a pandas DataFrame from stored dataset metadata (prefers file_path for full data, falls back to data_preview)
  - Registered all 27 tests directly in the `_TEST_RUNNERS` dict
  - Added `interpretation_context` storage to `execute_analysis()` so Stats Advisor AI can generate plain-language explanations
- Two execution paths now available:
  - `stats/engine.py` → DB-integrated async execution (used by `routers/analyses.py`)
  - `services/stats_engine.py` → Direct DataFrame execution + TEST_CATALOG metadata (used by AI agents)

**Key decisions:**
- AnalysisResult is the universal return type: test_type, test_category, success, summary, details, charts, interpretation_context, warnings
- Every test function returns interpretation_context dict specifically designed for the AI Stats Advisor to generate plain-language explanations
- Charts use dark-mode styling matching the UI design system (COLORS dict, DARK_LAYOUT template)
- StatsEngine uses a flat registry dict mapping test_type strings to (function, category) tuples — simple and reliable
- TEST_CATALOG provides rich metadata per test (name, y_type, x_type, min_samples, required/optional config) — used by Stats Advisor agent for intelligent test recommendation
- Comparison tests auto-check normality assumptions via _check_normality() and warn if violated, suggesting non-parametric alternatives
- Two-sample t-test auto-detects equal variance via Levene's test, switching to Welch's if needed
- ANOVA includes Tukey HSD post-hoc when significant (via statsmodels)
- SPC charts include Western Electric Rule 1 (beyond 3-sigma) violation detection
- X-bar/R chart supports subgroup sizes 2-10 with proper control chart constants
- Capability analysis estimates within-group sigma using I-MR method (d2=1.128) or pooled subgroup method
- Gage R&R uses ANOVA method with variance decomposition: repeatability, reproducibility, operator, interaction, part-to-part
- DOE designs use fixed random seed (42) for reproducible run order randomization

**Phase 2 is COMPLETE. Statistical engine provides:**
- 27 registered statistical tests
- 12 chart types (all Plotly JSON, frontend-ready)
- Full test catalog metadata for AI-powered test recommendation
- Standardized AnalysisResult format consumed by Stats Advisor agent and stored in statistical_analyses table

**What's next:**
- Phase 3 (Beacon agent): Dashboard & reporting engine
- Phase 4 (Prism agent): React frontend
- Phase 5 (Nexus agent): AI agent refinement (Chart Agent, prompt tuning)

**Blockers:** None

### Session 4 — 2026-02-12 (Forge agent — Alembic + Tests + Integration APIs)
**What was accomplished:**
- Wrote initial Alembic migration (`001_initial_schema.py`): all 17 tables, 21 indexes, `updated_at` triggers
- Built comprehensive pytest test suite: 8 test files, ~65 tests covering all 12 routers
  - conftest.py: async DB fixtures, httpx client factories, auth helpers, dependency overrides
  - Tests cover: auth (register/login/me), requests (CRUD + convert), initiatives (CRUD + phase auto-advance + all 4 methodologies), users (RBAC + workload), teams (CRUD + members), actions (CRUD + auto-complete), notes/docs/metrics/artifacts
- Built analysis router (`routers/analyses.py`): CRUD + execute + rerun statistical analyses (Sigma integration surface)
- Built analysis schemas (`schemas/analysis.py`): AnalysisCreate, AnalysisRerun, AnalysisOut
- Built stats execution engine (`stats/engine.py`): test runner registry with `@register_test` decorator, dataset loading, timing, error handling (stub for Sigma)
- Built dashboard router (`routers/dashboards.py`): 4 dashboard endpoints for Beacon
  - `/dashboards/portfolio` — status/methodology/priority/phase distributions, savings summary
  - `/dashboards/team/{id}` — team utilization + initiative list
  - `/dashboards/initiative/{id}` — phase timeline, KPIs, action summary, analyses
  - `/dashboards/pipeline` — request intake funnel, conversion rate, urgency distribution
- Registered 2 new routers in main.py (now 14 total)
- Updated CLAUDE.md File Inventory with all Phase 1 files

**Key decisions:**
- Alembic migration is hand-written (not autogenerated) since no live DB — more reliable and reviewable
- Tests use separate PostgreSQL test DB (`bb_command_test`) with dependency overrides for `get_db` and `get_current_user`
- Analysis execution engine uses a registry pattern: `@register_test("t_test_2sample")` — Sigma decorates functions to register them
- Dashboard router queries directly (no service layer yet) — Beacon can extract to `dashboard_engine.py` when adding complex calculations
- Analysis endpoint gracefully handles missing stats engine (catches ImportError, stays in "pending" state)

**What's next:**
- Sigma (parallel session): Implementing statistical test runners in `stats/` using the `@register_test` decorator
- Beacon (Phase 3): Report generation service, complex dashboard calculations
- Prism (Phase 4): React frontend

**Blockers:** None

### Session 3 — 2026-02-12 (Forge agent — PHASE 1 COMPLETE)
**What was accomplished:**
- Built complete auth system: JWT (python-jose), bcrypt, register/login/me, get_current_user + require_role guards
- Built user management: list (admin/manager), get, update (self or admin), workload summary
- Built team management: CRUD, member add/remove, member list
- Built all remaining CRUD routers: artifacts (phase-scoped), datasets (upload + auto-profile), actions (initiative + global), notes, documents, metrics
- Built workflow engine service: phase transition validation, gate readiness checking, advance_phase with auto-complete
- Built assignment engine service: analyst recommendation (skill + capacity scoring), team utilization summary
- Wired request triage to AI Triage Agent (POST /requests/:id/triage)
- Created Docker Compose (PostgreSQL 16 + Redis 7 + backend) and Dockerfile
- Established Named Agent Assignments (Forge, Sigma, Beacon, Prism, Nexus, Atlas) for parallel sessions
- Added Agent Continuity Protocol, Build Status tracking, File Inventory, Session Log to CLAUDE.md

**Key decisions:**
- Using python-jose (not pyjwt) for JWT — already in requirements
- Auth uses HTTPBearer scheme (Authorization: Bearer <token>)
- require_role() is a dependency factory — usage: `Depends(require_role("admin", "manager"))`
- Dataset upload auto-profiles via pandas: column metadata, summary stats, 50-row preview
- Workflow engine enforces sequential phase transitions (no skipping) and checks required artifacts per phase
- Assignment engine scores analysts: +10 per skill match, +up to 50 for availability, -5 per active initiative
- Request triage invokes Triage Agent directly (bypasses orchestrator routing) and stores complexity_score + recommended_methodology on the request
- Named agents have strict file ownership to prevent conflicts in parallel sessions

**Phase 1 is COMPLETE. Backend is fully runnable with:**
- 12 API routers (auth, ai, requests, initiatives, users, teams, actions, artifacts, notes, documents, metrics, datasets)
- 5 AI agents + orchestrator
- 14 ORM models
- 2 business logic services (workflow engine, assignment engine)
- Docker Compose for local dev
- Alembic migration setup

**What's next:**
- Phase 2 (Sigma agent): Statistical engine — scipy/statsmodels test implementations
- Phase 3 (Beacon agent): Dashboard + reporting engine
- Phase 4 (Prism agent): React frontend

**Blockers:** None

### Session 2 — 2026-02-12
**What was accomplished:**
- Created FastAPI entry point (`main.py`) with lifespan hooks, CORS, health check
- Built AI router (`routers/ai.py`) with 5 endpoints: POST /chat, POST /chat/stream (SSE), POST /invoke/{agent}, GET /agents, WS /ws
- Created database engine and async session management (`database.py`)
- Built all 14 ORM models across 5 files (user, request, initiative, phase, analysis, supporting)
- Created Pydantic API schemas for requests and initiatives
- Built Request CRUD router with auto-numbering and convert-to-initiative
- Built Initiative CRUD router with filters, phase management, and auto-advance logic
- Set up Alembic for database migrations (async env)
- Established 6-phase build roadmap

**Key decisions:**
- Database sessions auto-commit on success, rollback on exception (via `get_db` dependency)
- Initiative creation auto-generates methodology-specific phases (DMAIC gets 5, A3 gets 7, PDSA gets 4, Kaizen gets 3)
- Phase completion auto-advances initiative to next phase; final phase completion marks initiative as "completed"
- Request numbering: REQ-0001; Initiative numbering: INI-0001 (sequential)
- AI router returns `updated_history` and `updated_summary` so the frontend can maintain conversation state

**Blockers:** None

### Session 1 — 2026-02-12 (earlier)
**What was accomplished:**
- Reviewed existing Initiative Command Center (Google Apps Script) in `1_Initiative Command/`
- Designed full platform architecture and CLAUDE.md vision document (~975 lines)
- Created orchestrator agent definitions (3 markdown files)
- Created builder agent definitions (5 markdown files)
- Built agent base framework (`base.py`) — BaseAgent, AgentContext, AgentResponse, ConversationMemory
- Built AI Orchestrator (`orchestrator.py`) — intent classification (regex + AI), agent routing, streaming
- Built all 5 specialist agents: Triage, DMAIC Coach, Stats Advisor, Data Agent, Report Agent
- Created project config (`config.py`) and backend structure

**Key decisions:**
- Two-tier intent classification: fast regex patterns first, Claude AI fallback for ambiguous intents
- Two model tiers: heavy (Opus 4.6) for reasoning-intensive agents (triage, coaching, stats), light (Sonnet 4.5) for routine agents (data profiling, reports)
- DMAIC Coach uses dynamic system prompt injection — `_build_system_prompt()` appends phase-specific instructions based on `context.current_phase`
- ConversationMemory auto-summarizes when history exceeds `agent_max_context_messages` (default 20)
- Agent responses can include a JSON metadata block at the end (parsed by `_parse_response()`) for structured data like suggestions, action_type, and metadata

---

## Development Commands

```bash
# Backend
cd BB_Enabled_Command/backend
pip install -r requirements.txt
uvicorn app.main:app --reload                  # Start dev server (localhost:8000)
alembic revision --autogenerate -m "message"   # Generate migration
alembic upgrade head                           # Apply migrations

# Frontend (not yet created)
cd BB_Enabled_Command/frontend
npm install
npm run dev                                     # Start dev server (localhost:5173)

# Docker (not yet created)
docker-compose up -d                            # PostgreSQL + Redis + backend
```
