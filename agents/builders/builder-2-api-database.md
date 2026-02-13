# Builder 2: API & Database Agent

## Ownership
You own the core backend infrastructure:
- `backend/app/main.py` — FastAPI application entry
- `backend/app/config.py` — Environment configuration
- `backend/app/database.py` — SQLAlchemy engine, session management
- `backend/app/models/` — All SQLAlchemy ORM models
- `backend/app/schemas/` — All Pydantic request/response schemas
- `backend/app/routers/` — All FastAPI route handlers
- `backend/alembic/` — Database migrations
- `backend/app/middleware/` — Auth, CORS, logging, rate limiting

## Mission
Build a clean, well-documented REST API that serves as the backbone connecting the frontend, AI agents, statistical engine, and reporting system. Your schemas are the source of truth that every other builder depends on.

## Tech Stack (locked)
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic for migrations
- Pydantic v2 for schemas
- PostgreSQL 16
- Redis (for Celery task queue)
- python-jose for JWT auth
- python-multipart for file uploads

## What You Build

### 1. Database Models
Implement every table defined in the CLAUDE.md data model as SQLAlchemy ORM models:
- `User`, `Team`, `TeamMember`
- `Request`
- `Initiative`
- `Phase`, `PhaseArtifact`
- `Dataset`, `StatisticalAnalysis`
- `AIConversation`
- `ActionItem`
- `InitiativeStakeholder`, `ExternalStakeholder`
- `Note`, `Document`
- `Metric`
- `WorkloadEntry`

Every model must have:
- Proper relationships (foreign keys, backrefs)
- Indexes on frequently queried columns (status, initiative_id, user_id, created_at)
- Sensible defaults matching CLAUDE.md specifications
- `created_at` and `updated_at` timestamps with auto-update

### 2. Pydantic Schemas
For every model, create:
- `{Model}Create` — request body for creation (excludes id, timestamps)
- `{Model}Update` — partial update (all fields optional)
- `{Model}Response` — full response (includes id, timestamps, computed fields)
- `{Model}Brief` — lightweight response for list views (subset of fields)

These schemas are THE contract. Builder 1 generates TypeScript types from them. Do not change field names or types without coordinating through the System Architect.

### 3. API Endpoints
Implement every endpoint group defined in the CLAUDE.md API Contract:

**Auth & Users** — JWT-based authentication, role-based access control
- Login returns `{ access_token, token_type, user }`
- All protected endpoints require `Authorization: Bearer <token>` header
- Role hierarchy: admin > manager > analyst > viewer

**Requests** — Full CRUD + triage endpoint that calls AI orchestrator
**Initiatives** — Full CRUD + summary endpoint that calls AI
**Phases** — CRUD within initiative context + gate review endpoint
**Artifacts** — CRUD within phase context, JSONB content varies by artifact_type
**Datasets** — Multipart upload, auto-profile via stats engine call
**Analyses** — Trigger statistical test via stats engine, store results
**AI** — Proxy to AI orchestrator service, WebSocket for streaming
**Actions** — Full CRUD + global list with cross-initiative filtering
**Stakeholders, Notes, Documents, Metrics** — Standard CRUD patterns
**Dashboards** — Aggregation queries returning roll-up data
**Reports** — Trigger report generation via reporting service

### 4. Middleware
- **Auth Middleware** — Validate JWT on every request, inject current user into request state
- **CORS** — Allow frontend origin
- **Request Logging** — Log method, path, status, duration for every request
- **Rate Limiting** — Per-user rate limits on AI endpoints (prevent runaway API costs)
- **Error Handling** — Global exception handler returning standard error format:
  ```json
  { "error": "not_found", "detail": "Initiative INI-0042 not found", "status_code": 404 }
  ```

### 5. Database Migrations
- Initial migration creates all tables
- Seed migration creates default admin user and sample data
- Every schema change gets its own migration with descriptive name

### 6. Service Interfaces
You define the interfaces that Builders 3, 4, and 5 must implement:

```python
# stats_engine interface (Builder 3 implements)
class StatsEngine:
    async def profile_dataset(self, dataset_id: UUID) -> DatasetProfile: ...
    async def run_test(self, test_type: str, config: dict, dataset_id: UUID) -> AnalysisResult: ...
    async def get_available_tests(self, dataset_profile: DatasetProfile) -> list[TestRecommendation]: ...

# ai_orchestrator interface (Builder 4 implements)
class AIOrchestrator:
    async def route(self, intent: str, context: dict) -> AgentResponse: ...
    async def stream(self, intent: str, context: dict) -> AsyncGenerator[AgentResponse]: ...
    async def triage_request(self, request_data: dict) -> TriageResult: ...

# report_generator interface (Builder 5 implements)
class ReportGenerator:
    async def generate_executive_brief(self, filters: dict) -> bytes: ...  # PDF
    async def generate_initiative_report(self, initiative_id: UUID) -> bytes: ...  # PDF
    async def generate_phase_report(self, initiative_id: UUID, phase: str) -> str: ...  # HTML
```

You create stub implementations that return mock data so Builder 1 can develop against real API responses before Builders 3/4/5 are complete.

## Pagination Pattern

All list endpoints must support:
```
GET /initiatives?page=1&page_size=25&sort=created_at&order=desc&status=active&priority=high
```

Response:
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 25,
  "has_more": true
}
```

## Filtering Pattern

Use query parameters for filtering. Support multiple values with comma separation:
```
GET /initiatives?status=active,on_hold&priority=critical,high&team_id=uuid
```

## What You Do NOT Build
- Frontend components (Builder 1)
- Statistical test implementations (Builder 3) — you call the stats engine interface
- AI agent prompts and logic (Builder 4) — you call the AI orchestrator interface
- Dashboard calculation logic (Builder 5) — you expose the endpoints, they provide the queries

## Critical Outputs Other Builders Depend On
1. **Pydantic schemas** → Builder 1 uses these to generate TypeScript types
2. **Mock/stub service implementations** → Builder 1 can develop against real API before Builders 3/4/5 finish
3. **Database schema** → All builders query this schema
4. **Service interfaces** → Builders 3, 4, 5 implement these exact interfaces
