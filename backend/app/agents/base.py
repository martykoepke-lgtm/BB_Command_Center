"""
Base agent framework for BB Enabled Command.

All AI agents inherit from BaseAgent. This provides:
- Anthropic Claude API integration
- Conversation memory management with automatic summarization
- Structured context injection
- Standardized response format
- Streaming support for real-time UI updates
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncGenerator
from uuid import UUID

import anthropic
from pydantic import BaseModel, Field

from app.config import get_settings


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    TRIAGE = "triage"
    DMAIC_COACH = "dmaic_coach"
    STATS_ADVISOR = "stats_advisor"
    DATA_AGENT = "data_agent"
    CHART_AGENT = "chart_agent"
    REPORT_AGENT = "report_agent"
    STATS_VALIDATOR = "stats_validator"


class ActionType(str, Enum):
    """Actions the agent can request from the user or system."""
    NONE = "none"
    UPLOAD_DATA = "upload_data"
    RUN_TEST = "run_test"
    REVIEW_GATE = "review_gate"
    ASSIGN_TASK = "assign_task"
    CREATE_ARTIFACT = "create_artifact"
    APPROVE_RECOMMENDATION = "approve_recommendation"


class AgentContext(BaseModel):
    """Rich context passed to every agent invocation."""

    # Who is asking
    user_id: UUID | None = None
    user_name: str = ""
    user_role: str = ""  # admin, manager, analyst, viewer, sponsor

    # What initiative (if any)
    initiative_id: UUID | None = None
    initiative_title: str = ""
    problem_statement: str = ""
    desired_outcome: str = ""
    methodology: str = ""
    current_phase: str = ""
    initiative_status: str = ""
    initiative_priority: str = ""

    # Phase state
    phase_artifacts: list[dict] = Field(default_factory=list)
    all_phases_status: dict = Field(default_factory=dict)

    # Related data
    recent_notes: list[dict] = Field(default_factory=list)
    recent_actions: list[dict] = Field(default_factory=list)
    dataset_profiles: list[dict] = Field(default_factory=list)
    analysis_results: list[dict] = Field(default_factory=list)
    stakeholders: list[dict] = Field(default_factory=list)
    metrics: list[dict] = Field(default_factory=list)

    # Conversation state
    conversation_history: list[dict] = Field(default_factory=list)
    conversation_summary: str | None = None

    # Extra context (agent-specific)
    extra: dict = Field(default_factory=dict)

    def to_system_context(self) -> str:
        """Format context as a readable string injected into the system prompt."""
        parts: list[str] = []

        if self.initiative_title:
            parts.append(f"## Current Initiative: {self.initiative_title}")
            parts.append(f"- Problem: {self.problem_statement}")
            parts.append(f"- Desired Outcome: {self.desired_outcome}")
            parts.append(f"- Methodology: {self.methodology}")
            parts.append(f"- Current Phase: {self.current_phase}")
            parts.append(f"- Status: {self.initiative_status} | Priority: {self.initiative_priority}")

        if self.all_phases_status:
            parts.append("\n## Phase Status")
            for phase, status in self.all_phases_status.items():
                icon = {"completed": "✅", "in_progress": "🔄", "not_started": "○"}.get(status, "○")
                parts.append(f"  {icon} {phase.title()}: {status}")

        if self.phase_artifacts:
            parts.append(f"\n## Artifacts in {self.current_phase.title()} Phase")
            for art in self.phase_artifacts:
                status = art.get("status", "draft")
                parts.append(f"  - {art.get('title', 'Untitled')} [{status}]")

        if self.recent_notes:
            parts.append("\n## Recent Notes")
            for note in self.recent_notes[:3]:
                date = note.get("created_at", "")[:10]
                parts.append(f"  - [{date}] {note.get('note_type', 'General')}: {note.get('content', '')[:200]}")

        if self.recent_actions:
            open_actions = [a for a in self.recent_actions if a.get("status") != "completed"]
            if open_actions:
                parts.append(f"\n## Open Action Items ({len(open_actions)})")
                for action in open_actions[:5]:
                    due = action.get("due_date", "no date")
                    parts.append(f"  - {action.get('title', '')} (owner: {action.get('owner_name', 'unassigned')}, due: {due})")

        if self.dataset_profiles:
            parts.append(f"\n## Uploaded Datasets ({len(self.dataset_profiles)})")
            for ds in self.dataset_profiles:
                parts.append(f"  - {ds.get('name', 'Untitled')}: {ds.get('row_count', '?')} rows, {ds.get('column_count', '?')} columns")

        if self.analysis_results:
            parts.append(f"\n## Completed Analyses ({len(self.analysis_results)})")
            for an in self.analysis_results[:5]:
                parts.append(f"  - {an.get('test_type', 'Unknown')}: p={an.get('p_value', 'N/A')}")

        if self.metrics:
            parts.append(f"\n## Tracked Metrics ({len(self.metrics)})")
            for m in self.metrics:
                baseline = m.get("baseline_value", "?")
                current = m.get("current_value", "?")
                target = m.get("target_value", "?")
                parts.append(f"  - {m.get('name', '')}: baseline={baseline}, current={current}, target={target}")

        if self.conversation_summary:
            parts.append(f"\n## Conversation Summary (prior context)\n{self.conversation_summary}")

        return "\n".join(parts) if parts else "No initiative context available."


class AgentResponse(BaseModel):
    """Standardized response from any agent."""
    agent_type: str
    content: str
    suggestions: list[str] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    context_update: dict = Field(default_factory=dict)
    requires_action: bool = False
    action_type: str = ActionType.NONE
    metadata: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Subclasses must implement:
    - agent_type: the AgentType enum value
    - system_prompt: the core system prompt (before context injection)
    - model: which Claude model to use (heavy or light)

    The base class handles:
    - Claude API calls (sync and streaming)
    - Context injection into system prompt
    - Conversation history formatting
    - Response parsing into AgentResponse
    """

    def __init__(self):
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Which agent type this is."""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Core system prompt. Context is appended automatically."""

    @property
    def model(self) -> str:
        """Which Claude model to use. Override in subclasses for light model."""
        return self._settings.ai_model_heavy

    def _build_system_prompt(self, context: AgentContext) -> str:
        """Combine the agent's system prompt with initiative context."""
        context_str = context.to_system_context()
        return f"{self.system_prompt}\n\n---\n\n# Current Context\n{context_str}"

    def _format_messages(self, context: AgentContext, user_message: str) -> list[dict]:
        """Build the messages array from conversation history + new user message."""
        messages: list[dict] = []

        # Include recent conversation history
        for msg in context.conversation_history[-(self._settings.agent_max_context_messages):]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add the new user message
        messages.append({"role": "user", "content": user_message})
        return messages

    async def invoke(self, user_message: str, context: AgentContext) -> AgentResponse:
        """
        Send a message to the agent and get a complete response.

        Args:
            user_message: What the user said or what triggered this agent
            context: Full project context for this interaction

        Returns:
            AgentResponse with the agent's reply, suggestions, and any requested actions
        """
        system = self._build_system_prompt(context)
        messages = self._format_messages(context, user_message)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self._settings.agent_max_tokens,
            temperature=self._settings.agent_temperature,
            system=system,
            messages=messages,
        )

        content = response.content[0].text if response.content else ""
        return self._parse_response(content)

    async def stream(self, user_message: str, context: AgentContext) -> AsyncGenerator[str, None]:
        """
        Stream a response token-by-token for real-time UI display.

        Yields partial content strings as they arrive from the API.
        """
        system = self._build_system_prompt(context)
        messages = self._format_messages(context, user_message)

        with self._client.messages.stream(
            model=self.model,
            max_tokens=self._settings.agent_max_tokens,
            temperature=self._settings.agent_temperature,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def _parse_response(self, raw_content: str) -> AgentResponse:
        """
        Parse agent output into structured AgentResponse.

        Agents can optionally include structured data in their response
        using a JSON block at the end:

        ```json
        {"suggestions": [...], "action_type": "run_test", ...}
        ```

        If no JSON block is found, the entire content is treated as the response text.
        """
        content = raw_content
        suggestions: list[str] = []
        action_type = ActionType.NONE
        requires_action = False
        artifacts: list[dict] = []
        metadata: dict = {}

        # Check if the response ends with a JSON metadata block
        if "```json" in raw_content:
            parts = raw_content.rsplit("```json", 1)
            if len(parts) == 2 and "```" in parts[1]:
                content = parts[0].rstrip()
                json_str = parts[1].split("```")[0].strip()
                try:
                    meta = json.loads(json_str)
                    suggestions = meta.get("suggestions", [])
                    action_str = meta.get("action_type", "none")
                    if action_str in ActionType.__members__.values():
                        action_type = action_str
                    requires_action = meta.get("requires_action", False)
                    artifacts = meta.get("artifacts", [])
                    metadata = meta.get("metadata", {})
                except json.JSONDecodeError:
                    pass  # If JSON parsing fails, treat entire output as content

        return AgentResponse(
            agent_type=self.agent_type.value,
            content=content,
            suggestions=suggestions,
            requires_action=requires_action,
            action_type=action_type,
            artifacts=artifacts,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Conversation Memory Manager
# ---------------------------------------------------------------------------

class ConversationMemory:
    """
    Manages conversation history with automatic summarization for long conversations.

    When conversation exceeds max_messages, older messages are compressed into a
    summary using Claude, and only recent messages + summary are retained.
    """

    def __init__(self, max_messages: int | None = None):
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._max_messages = max_messages or settings.agent_max_context_messages
        self._light_model = settings.ai_model_light

    async def prepare_context(
        self,
        messages: list[dict],
        existing_summary: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """
        Prepare conversation messages for context injection.

        If messages exceed max_messages, summarize the older ones and return
        the summary + recent messages.

        Returns:
            (recent_messages, updated_summary)
        """
        if len(messages) <= self._max_messages:
            return messages, existing_summary

        # Split: older messages to summarize, recent messages to keep
        split_point = len(messages) - (self._max_messages // 2)
        older = messages[:split_point]
        recent = messages[split_point:]

        # Build summary from older messages + any existing summary
        summary = await self._summarize(older, existing_summary)
        return recent, summary

    async def _summarize(self, messages: list[dict], existing_summary: str | None) -> str:
        """Compress older messages into a concise summary."""
        context = ""
        if existing_summary:
            context = f"Previous conversation summary:\n{existing_summary}\n\n"

        message_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content'][:500]}"
            for m in messages
        )

        response = self._client.messages.create(
            model=self._light_model,
            max_tokens=1024,
            temperature=0.1,
            system="You summarize conversations concisely. Preserve key decisions, findings, data points, and action items. Omit pleasantries and repetition.",
            messages=[{
                "role": "user",
                "content": f"{context}Summarize this conversation, preserving all important context:\n\n{message_text}",
            }],
        )
        return response.content[0].text if response.content else ""
