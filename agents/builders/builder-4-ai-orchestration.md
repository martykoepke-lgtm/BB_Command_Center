# Builder 4: AI Agent System Agent

## Ownership
You own:
- `backend/app/agents/` — All AI agent definitions, prompts, and logic
- `backend/app/services/ai_orchestrator.py` — The orchestrator that routes user intent to agents

## Mission
Build the AI brain of the platform. This is what makes BB Enabled Command fundamentally different from every other tool. The AI doesn't just answer questions — it actively drives methodology, coaches users through each phase, recommends statistical approaches, interprets results, and generates reports. It has full project context at every interaction.

## Tech Stack (locked)
- Anthropic Claude API (claude-opus-4-6 for complex reasoning, claude-sonnet-4-5-20250929 for routine tasks)
- anthropic Python SDK
- WebSocket streaming for real-time agent responses

## What You Build

### 1. Orchestrator (`agents/orchestrator.py`)

The central router that determines which agent handles a user's request:

```python
class AIOrchestrator:
    async def route(self, intent: str, context: AgentContext) -> AgentResponse:
        """
        Analyze user intent and route to the appropriate agent.

        Routing logic:
        - If in request intake and triage needed → Triage Agent
        - If asking about methodology, phase work, or process → DMAIC Coach
        - If asking about data, statistics, or analysis → Stats Advisor
        - If data was just uploaded → Data Agent (auto-triggered)
        - If requesting a report or summary → Report Agent
        - If asking about a chart or visualization → Chart Agent
        - If general question about the initiative → DMAIC Coach (default)
        """

    async def stream(self, intent: str, context: AgentContext) -> AsyncGenerator[str, None]:
        """Stream agent response for real-time display in the AI panel."""

    def build_context(self, initiative_id: UUID, phase: str = None) -> AgentContext:
        """
        Build the full context an agent needs:
        - Initiative details (problem statement, scope, current phase, status)
        - Phase artifacts completed so far
        - Recent notes and action items
        - Dataset profiles and analysis results
        - Conversation history (summarized if long)
        """
```

### 2. Agent Context

Every agent receives rich project context:

```python
class AgentContext(BaseModel):
    user: dict                    # current user info (name, role)
    initiative: dict | None       # initiative details
    current_phase: str | None     # which DMAIC phase
    phase_artifacts: list[dict]   # artifacts completed in current phase
    all_phases_status: dict       # { "define": "completed", "measure": "in_progress", ... }
    recent_notes: list[dict]      # last 5 notes
    recent_actions: list[dict]    # open action items
    dataset_profiles: list[dict]  # uploaded dataset summaries
    analysis_results: list[dict]  # completed statistical analyses
    conversation_history: list[dict]  # recent messages in this conversation
    conversation_summary: str | None  # compressed summary of older conversation
```

### 3. Triage Agent (`agents/triage_agent.py`)

Activated on new request submission.

**System prompt core:**
```
You are a Performance Excellence triage specialist. Analyze incoming improvement requests
and provide a structured assessment.

Given a problem statement and desired outcome, you must:
1. Score complexity (1-10) based on: scope breadth, data requirements, stakeholder count,
   organizational change needed, technical difficulty
2. Recommend methodology:
   - DMAIC (score 6-10): Complex, data-driven, multiple root causes possible
   - A3 (score 4-6): Mid-complexity, structured problem-solving, single-page format
   - Kaizen (score 3-5): Quick win opportunity, solution is partially known, can be done in 1-5 days
   - PDSA (score 3-5): Iterative testing needed, hypothesis-driven
   - Just-Do-It (score 1-3): Obvious fix, no data analysis needed, just implement
3. Identify key questions that need answering before starting
4. Suggest initial stakeholders to involve
5. Estimate timeline range
```

**Output format:**
```python
class TriageResult(BaseModel):
    complexity_score: int          # 1-10
    complexity_reasoning: str
    recommended_methodology: str   # DMAIC, A3, Kaizen, PDSA, just_do_it
    methodology_reasoning: str
    key_questions: list[str]       # 3-5 questions to clarify before starting
    suggested_stakeholders: list[str]  # roles, not names
    estimated_timeline: str        # "4-8 weeks" or "1-2 days"
    risks: list[str]               # potential challenges
```

### 4. DMAIC Coach (`agents/dmaic_coach.py`)

The primary coaching agent. Phase-aware — behavior changes based on which phase the initiative is in.

**System prompt core:**
```
You are an expert Lean Six Sigma Black Belt coach. You guide analysts through the DMAIC
methodology with rigor and thoroughness. You ask probing questions to ensure nothing is missed.
You praise good work and challenge incomplete thinking.

Your personality:
- Direct but supportive
- Always ask "why" and "how do you know"
- Push for data-driven decisions, not opinions
- Celebrate progress and completed gates
- Flag when something is being skipped or done superficially

You have access to the full initiative context including all artifacts, data, and analysis results.
Use this context to give specific, relevant guidance — not generic advice.
```

**Phase-specific behavior (loaded dynamically):**

**Define phase prompts:**
- "Let's make sure your problem statement is quantified. What metric captures this problem? What is its current value?"
- "Your SIPOC looks good, but I notice the process boundaries aren't clearly defined. Where exactly does the process start and end?"
- "Who is the voice of the customer here? Have you talked to actual patients/staff/customers about this problem?"
- "Your goal statement says 'improve wait times.' Let's make that SMART — by how much, by when?"

**Measure phase prompts:**
- "Before collecting data, let's verify your measurement system. How confident are you that your data source is accurate and consistent?"
- "What's your sampling strategy? Are you collecting enough data to detect the difference you're looking for?"
- "I see you've collected 25 data points. For the analysis you'll likely need, 30+ is recommended. Can you collect more?"
- "Your baseline Cpk is 0.67 — that confirms the process needs improvement. Good baseline measurement."

**Analyze phase prompts:**
- "You've identified 12 potential root causes on your fishbone. Which ones have you been able to validate with data?"
- "The ANOVA shows a significant difference between shifts (p=0.003). But is this practically significant? What's the actual difference in means?"
- "Before we accept these vital X's, have you checked for confounding variables?"
- "Your regression R-squared is 0.34 — that means your model explains 34% of the variation. What else might be driving the other 66%?"

**Improve phase prompts:**
- "You have 4 potential solutions. Let's prioritize — which ones address the validated root causes from your Analyze phase?"
- "What does your pilot plan look like? Where will you test, for how long, and how will you measure success?"
- "The pilot results look promising — a 28% improvement. But is this statistically significant, or could it be normal variation?"

**Control phase prompts:**
- "Your control plan needs a reaction plan for each monitoring point. What happens when the control chart shows an out-of-control signal?"
- "Who is the process owner going forward? Have they been trained on the control plan?"
- "Let's calculate the sustained financial impact. Is the improvement holding over time?"

### 5. Stats Advisor (`agents/stats_advisor.py`)

Specialized agent for statistical analysis guidance.

**System prompt core:**
```
You are a statistical analysis advisor for Lean Six Sigma projects. You help users choose
the right statistical test, configure it correctly, and understand the results.

You MUST:
- Ask about the data types (continuous/categorical) of Y and X variables
- Consider sample size adequacy
- Check assumptions before recommending a test
- Explain WHY a test is appropriate, not just which test to run
- After results: explain in plain language what the numbers mean for the business
- Suggest follow-up analyses when appropriate

NEVER recommend a test without understanding the data structure first.
ALWAYS translate statistical output into business language.
```

**Interaction flow:**
```
User: "I need to analyze my data"
Advisor: "Let me look at your dataset. You have [describe columns and types].
          What is your Y variable (the outcome you're trying to improve)?
          And what X variables (potential causes) do you want to test?"

User: "Y is wait_time, X is shift"
Advisor: "Wait time is continuous and shift has 3 categories (Day, Evening, Night).
          With 45 observations per shift, I recommend a One-Way ANOVA to test if
          mean wait times differ significantly across shifts.

          Before we run it, I need to check two assumptions:
          1. Normality within each group
          2. Equal variances across groups

          Want me to run these checks first?"

User: "Yes"
[Stats engine runs normality + Levene's test]
Advisor: "Normality: All three groups pass Shapiro-Wilk (p > 0.05). Good.
          Equal variance: Levene's test p = 0.34 — variances are equal. Good.

          All assumptions met. Running One-Way ANOVA now..."

[Stats engine runs ANOVA]
Advisor: "Results:
          F-statistic: 8.42, p-value: 0.0004

          This means there IS a statistically significant difference in wait times
          across shifts. Running Tukey's post-hoc to see which shifts differ...

          Night shift (avg 4.8 hrs) is significantly longer than Day (avg 3.1 hrs)
          and Evening (avg 3.4 hrs). Day and Evening are not significantly different.

          Night shift wait times are 55% higher than Day shift.
          This suggests investigating what's different about the Night shift process
          as a potential root cause.

          Want me to run a Pareto analysis on Night shift wait time reasons?"
```

### 6. Data Agent (`agents/data_agent.py`)

Auto-triggered when a dataset is uploaded.

**Responsibilities:**
- Profile the data (calls stats engine's `profile_dataset`)
- Flag quality issues (missing values, outliers, wrong data types)
- Suggest data transformations
- Generate descriptive summary
- Store profile in the dataset record

### 7. Report Agent (`agents/report_agent.py`)

Generates narrative content for reports.

**Responsibilities:**
- Phase gate summaries ("Here's what was accomplished in the Define phase...")
- Initiative executive summaries
- Statistical analysis translations for non-technical audiences
- Project close-out narratives (before/after story)

### Agent Response Format (must match CLAUDE.md)

```python
class AgentResponse(BaseModel):
    agent_type: str              # triage, dmaic_coach, stats_advisor, data_agent, report_agent
    content: str                 # the response text (markdown supported)
    suggestions: list[str]       # clickable follow-up options
    artifacts: list[dict]        # generated content (chart specs, templates, etc.)
    context_update: dict         # updates to conversation context
    requires_action: bool        # does the user need to do something?
    action_type: str | None      # upload_data, run_test, review_gate, assign_task, etc.
```

### Conversation Memory

For long initiatives that span weeks/months:

```python
class ConversationManager:
    async def get_context(self, initiative_id: UUID, agent_type: str) -> list[dict]:
        """
        Return conversation history for this initiative + agent.
        If history exceeds 20 messages, compress older messages into a summary
        and return summary + last 10 messages.
        """

    async def summarize(self, messages: list[dict]) -> str:
        """Use Claude to compress older messages into a context summary."""

    async def save_message(self, initiative_id: UUID, agent_type: str, role: str, content: str): ...
```

### Model Selection

- **claude-opus-4-6** — Triage Agent (complex assessment), DMAIC Coach (nuanced coaching), Stats Advisor (reasoning about statistical approaches)
- **claude-sonnet-4-5-20250929** — Data Agent (routine profiling), Report Agent (structured generation), conversation summarization

## What You Do NOT Build
- API endpoints (Builder 2 wraps your orchestrator in routes)
- Statistical computations (Builder 3 — you call their service)
- Frontend AI chat UI (Builder 1)
- Report HTML/PDF formatting (Builder 5)

## Dependencies
- **Builder 2** provides the data access layer (initiative details, artifacts, datasets)
- **Builder 3** provides `stats_engine.recommend_tests()` and `stats_engine.run_test()` for the Stats Advisor
- **Builder 5** provides report templates that the Report Agent fills with narrative content
