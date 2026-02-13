"""
AI Orchestrator — Central router that directs user intent to the right agent.

The Orchestrator is the brain of the multi-agent system. It:
1. Analyzes what the user is asking or what event just occurred
2. Determines which specialist agent should handle it
3. Builds the appropriate context for that agent
4. Routes the request and returns the response
5. Handles agent-to-agent handoffs (e.g., Stats Advisor triggers Data Agent)
"""

from __future__ import annotations

import re
from typing import AsyncGenerator
from uuid import UUID

from app.agents.base import (
    AgentContext,
    AgentResponse,
    AgentType,
    BaseAgent,
    ConversationMemory,
)
from app.config import get_settings


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class Intent:
    """Represents a classified user intent with confidence."""

    def __init__(self, agent_type: AgentType, confidence: float, reasoning: str):
        self.agent_type = agent_type
        self.confidence = confidence
        self.reasoning = reasoning


# Keyword patterns for fast intent routing (before falling back to AI classification)
INTENT_PATTERNS: list[tuple[AgentType, list[str]]] = [
    (AgentType.STATS_ADVISOR, [
        r"\b(statistic|anova|t-test|regression|correlation|p-value|hypothesis|chi.?square"
        r"|capability|cpk|control.?chart|normality|sample.?size|confidence.?interval"
        r"|pareto|gage|msa|doe|factorial)\b",
        r"\b(analyze|analysis|run.?test|which.?test|data.?analys)\b",
    ]),
    (AgentType.DATA_AGENT, [
        r"\b(upload|dataset|data.?quality|missing.?value|outlier|clean.?data"
        r"|column|row|csv|excel|import.?data|data.?profile)\b",
    ]),
    (AgentType.REPORT_AGENT, [
        r"\b(report|summary|executive.?brief|gate.?review|close.?out"
        r"|generate.?report|pdf|document.?the)\b",
    ]),
    (AgentType.TRIAGE, [
        r"\b(new.?request|intake|triage|classify|complexity|recommend.?methodology"
        r"|should.?we.?use.?dmaic|kaizen.?or|a3.?or)\b",
    ]),
]


def classify_intent_fast(message: str, context: AgentContext) -> Intent | None:
    """
    Rule-based fast classification. Returns None if no strong match,
    in which case the orchestrator falls back to AI-based classification.
    """
    message_lower = message.lower()

    for agent_type, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return Intent(
                    agent_type=agent_type,
                    confidence=0.85,
                    reasoning=f"Keyword match for {agent_type.value}",
                )

    # If we're in a specific phase and the message is general, default to coach
    if context.current_phase and context.initiative_id:
        return Intent(
            agent_type=AgentType.DMAIC_COACH,
            confidence=0.7,
            reasoning="Default to DMAIC coach — user is in an active initiative phase",
        )

    return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Routes user messages to the appropriate specialist agent.

    Flow:
    1. Try fast keyword-based classification
    2. If no confident match, use AI to classify intent
    3. Route to the matched agent
    4. Return the agent's response
    """

    def __init__(self):
        self._settings = get_settings()
        self._memory = ConversationMemory()
        self._agents: dict[AgentType, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialist agent for routing."""
        self._agents[agent.agent_type] = agent

    def get_agent(self, agent_type: AgentType) -> BaseAgent | None:
        """Get a registered agent by type."""
        return self._agents.get(agent_type)

    async def route(self, user_message: str, context: AgentContext) -> AgentResponse:
        """
        Classify intent and route to the appropriate agent.

        Args:
            user_message: The user's input
            context: Full initiative/project context

        Returns:
            AgentResponse from the specialist agent
        """
        # Step 1: Prepare conversation memory
        recent_messages, summary = await self._memory.prepare_context(
            context.conversation_history,
            context.conversation_summary,
        )
        context.conversation_history = recent_messages
        context.conversation_summary = summary

        # Step 2: Classify intent
        intent = classify_intent_fast(user_message, context)

        if intent is None or intent.confidence < 0.6:
            intent = await self._classify_with_ai(user_message, context)

        # Step 3: Route to agent
        agent = self._agents.get(intent.agent_type)
        if agent is None:
            # Fallback to DMAIC coach if available, otherwise return error
            agent = self._agents.get(AgentType.DMAIC_COACH)
            if agent is None:
                return AgentResponse(
                    agent_type="orchestrator",
                    content=f"No agent available for intent: {intent.agent_type.value}. "
                            f"Available agents: {', '.join(a.value for a in self._agents)}",
                )

        # Step 4: Invoke the agent
        response = await agent.invoke(user_message, context)

        # Step 5: Add routing metadata
        response.metadata["routed_by"] = "orchestrator"
        response.metadata["intent_agent"] = intent.agent_type.value
        response.metadata["intent_confidence"] = intent.confidence
        response.metadata["intent_reasoning"] = intent.reasoning

        return response

    async def stream_route(
        self, user_message: str, context: AgentContext
    ) -> AsyncGenerator[str, None]:
        """
        Classify intent and stream the response from the matched agent.

        Yields partial content strings for real-time UI display.
        """
        # Prepare memory
        recent_messages, summary = await self._memory.prepare_context(
            context.conversation_history,
            context.conversation_summary,
        )
        context.conversation_history = recent_messages
        context.conversation_summary = summary

        # Classify
        intent = classify_intent_fast(user_message, context)
        if intent is None or intent.confidence < 0.6:
            intent = await self._classify_with_ai(user_message, context)

        agent = self._agents.get(intent.agent_type)
        if agent is None:
            agent = self._agents.get(AgentType.DMAIC_COACH)

        if agent is None:
            yield "No agent available to handle this request."
            return

        # Stream from the agent
        async for chunk in agent.stream(user_message, context):
            yield chunk

    async def invoke_specific(
        self, agent_type: AgentType, user_message: str, context: AgentContext
    ) -> AgentResponse:
        """
        Bypass routing and invoke a specific agent directly.
        Used when the system knows exactly which agent to call
        (e.g., data uploaded → Data Agent, gate review requested → Coach).
        """
        agent = self._agents.get(agent_type)
        if agent is None:
            return AgentResponse(
                agent_type="orchestrator",
                content=f"Agent {agent_type.value} is not registered.",
            )
        return await agent.invoke(user_message, context)

    async def _classify_with_ai(self, user_message: str, context: AgentContext) -> Intent:
        """
        Use Claude to classify intent when keyword matching isn't confident enough.
        Uses the light model for speed.
        """
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

        available_agents = ", ".join(
            f"{a.value} ({self._agents[a].agent_type.value})"
            for a in self._agents
        )

        phase_info = f"Current phase: {context.current_phase}" if context.current_phase else "No active phase"
        init_info = f"Active initiative: {context.initiative_title}" if context.initiative_title else "No active initiative"

        response = client.messages.create(
            model=self._settings.ai_model_light,
            max_tokens=256,
            temperature=0.0,
            system=(
                "You are an intent classifier for a Performance Excellence platform. "
                "Given a user message and context, determine which specialist agent should handle it. "
                "Respond with ONLY a JSON object: {\"agent\": \"agent_type\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}\n\n"
                f"Available agents: {available_agents}\n"
                "Agent descriptions:\n"
                "- triage: Classifies new requests, recommends methodology (DMAIC/Kaizen/A3)\n"
                "- dmaic_coach: Guides users through DMAIC phases, asks probing questions, reviews artifacts\n"
                "- stats_advisor: Recommends statistical tests, interprets results, guides data analysis\n"
                "- data_agent: Profiles uploaded datasets, checks data quality, suggests transformations\n"
                "- report_agent: Generates reports, summaries, gate review documents\n"
                "- chart_agent: Creates visualizations and charts\n"
            ),
            messages=[{
                "role": "user",
                "content": f"Context: {init_info}. {phase_info}.\n\nUser message: {user_message}",
            }],
        )

        # Parse the classification response
        try:
            import json
            text = response.content[0].text if response.content else "{}"
            # Extract JSON from response (handle markdown code blocks)
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            result = json.loads(text)
            agent_str = result.get("agent", "dmaic_coach")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "AI classification")

            # Map string to AgentType
            agent_map = {a.value: a for a in AgentType}
            agent_type = agent_map.get(agent_str, AgentType.DMAIC_COACH)

            return Intent(agent_type, confidence, reasoning)

        except (json.JSONDecodeError, KeyError, ValueError):
            # Default to DMAIC coach on classification failure
            return Intent(
                AgentType.DMAIC_COACH,
                confidence=0.5,
                reasoning="Fallback — AI classification failed to parse",
            )


# ---------------------------------------------------------------------------
# Factory: Build and wire the full orchestrator with all agents
# ---------------------------------------------------------------------------

def create_orchestrator() -> Orchestrator:
    """
    Factory function that creates the orchestrator and registers all agents.
    Called once at application startup.
    """
    from app.agents.triage_agent import TriageAgent
    from app.agents.dmaic_coach import DMAICCoach
    from app.agents.stats_advisor import StatsAdvisor
    from app.agents.stats_validator import StatsValidatorAgent
    from app.agents.data_agent import DataAgent
    from app.agents.report_agent import ReportAgent

    orchestrator = Orchestrator()
    orchestrator.register_agent(TriageAgent())
    orchestrator.register_agent(DMAICCoach())
    orchestrator.register_agent(StatsAdvisor())
    orchestrator.register_agent(StatsValidatorAgent())
    orchestrator.register_agent(DataAgent())
    orchestrator.register_agent(ReportAgent())

    return orchestrator
