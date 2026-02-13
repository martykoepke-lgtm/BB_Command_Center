"""
AI Router — HTTP and WebSocket endpoints for the agent orchestrator.

Provides:
- POST /api/ai/chat           — Single-turn agent interaction (complete response)
- POST /api/ai/chat/stream    — Server-Sent Events stream for real-time token display
- POST /api/ai/stream         — SSE stream alias (frontend convenience)
- POST /api/ai/invoke/{agent} — Direct agent invocation by path (bypass routing)
- POST /api/ai/invoke         — Direct agent invocation by body (agent in JSON)
- GET  /api/ai/agents         — List available agents
- WS   /api/ai/ws             — WebSocket for bi-directional real-time chat
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.base import AgentContext, AgentResponse, AgentType
from app.agents.orchestrator import Orchestrator
from app.main import get_orchestrator

router = APIRouter(prefix="/ai", tags=["AI Agents"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Input for an AI chat interaction."""
    message: str = Field(..., min_length=1, max_length=10000)

    # Initiative context (optional — if user is working within an initiative)
    initiative_id: UUID | None = None
    initiative_title: str = ""
    problem_statement: str = ""
    desired_outcome: str = ""
    methodology: str = ""
    current_phase: str = ""
    initiative_status: str = ""
    initiative_priority: str = ""

    # Phase artifacts and data
    phase_artifacts: list[dict] = Field(default_factory=list)
    all_phases_status: dict = Field(default_factory=dict)
    dataset_profiles: list[dict] = Field(default_factory=list)
    analysis_results: list[dict] = Field(default_factory=list)
    metrics: list[dict] = Field(default_factory=list)

    # Conversation continuity
    conversation_history: list[dict] = Field(default_factory=list)
    conversation_summary: str | None = None

    # Caller identity
    user_id: UUID | None = None
    user_name: str = ""
    user_role: str = ""


class ChatResponse(BaseModel):
    """Output from an AI chat interaction."""
    agent_type: str
    content: str
    suggestions: list[str] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    requires_action: bool = False
    action_type: str = "none"
    metadata: dict = Field(default_factory=dict)
    timestamp: str = ""

    # Conversation state for the client to send back on next message
    updated_history: list[dict] = Field(default_factory=list)
    updated_summary: str | None = None


class AgentInfo(BaseModel):
    """Public info about a registered agent."""
    agent_type: str
    model: str
    description: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_context(req: ChatRequest) -> AgentContext:
    """Convert the flat ChatRequest into a rich AgentContext."""
    return AgentContext(
        user_id=req.user_id,
        user_name=req.user_name,
        user_role=req.user_role,
        initiative_id=req.initiative_id,
        initiative_title=req.initiative_title,
        problem_statement=req.problem_statement,
        desired_outcome=req.desired_outcome,
        methodology=req.methodology,
        current_phase=req.current_phase,
        initiative_status=req.initiative_status,
        initiative_priority=req.initiative_priority,
        phase_artifacts=req.phase_artifacts,
        all_phases_status=req.all_phases_status,
        dataset_profiles=req.dataset_profiles,
        analysis_results=req.analysis_results,
        metrics=req.metrics,
        conversation_history=req.conversation_history,
        conversation_summary=req.conversation_summary,
    )


def _agent_response_to_chat(
    resp: AgentResponse, context: AgentContext, user_message: str
) -> ChatResponse:
    """Convert internal AgentResponse to API ChatResponse, including updated history."""
    # Append this exchange to conversation history
    updated_history = list(context.conversation_history)
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": resp.content})

    return ChatResponse(
        agent_type=resp.agent_type,
        content=resp.content,
        suggestions=resp.suggestions,
        artifacts=resp.artifacts,
        requires_action=resp.requires_action,
        action_type=resp.action_type,
        metadata=resp.metadata,
        timestamp=resp.timestamp,
        updated_history=updated_history,
        updated_summary=context.conversation_summary,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Single-turn chat — sends user message through the orchestrator,
    returns the complete agent response.
    """
    context = _build_context(req)
    response = await orchestrator.route(req.message, context)
    return _agent_response_to_chat(response, context, req.message)


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Streaming chat — returns a Server-Sent Events stream so the frontend
    can render tokens as they arrive from the agent.

    Event format:
        data: {"type": "token", "content": "partial text"}
        data: {"type": "done", "agent_type": "dmaic_coach", "suggestions": [...]}
    """
    context = _build_context(req)

    async def event_stream() -> AsyncGenerator[str, None]:
        full_content = ""
        async for chunk in orchestrator.stream_route(req.message, context):
            full_content += chunk
            event_data = json.dumps({"type": "token", "content": chunk})
            yield f"data: {event_data}\n\n"

        # Send completion event with metadata
        done_data = json.dumps({
            "type": "done",
            "full_content": full_content,
            "suggestions": [],  # Parsed from full_content if JSON block present
        })
        yield f"data: {done_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream")
async def chat_stream_alias(
    req: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Alias for /chat/stream — frontend calls /api/ai/stream for convenience.
    Returns the same SSE stream.
    """
    return await chat_stream(req, orchestrator)


class InvokeByBodyRequest(ChatRequest):
    """Extends ChatRequest with an agent field for body-based invocation."""
    agent: str = Field(..., min_length=1, description="Agent type to invoke")


@router.post("/invoke", response_model=ChatResponse)
async def invoke_agent_by_body(
    req: InvokeByBodyRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Direct agent invocation with agent type in the request body.
    Frontend sends {agent: "coach", message: "...", context: {...}}.
    """
    try:
        target = AgentType(req.agent)
    except ValueError:
        valid = [a.value for a in AgentType]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent type '{req.agent}'. Valid types: {valid}",
        )

    context = _build_context(req)
    response = await orchestrator.invoke_specific(target, req.message, context)
    return _agent_response_to_chat(response, context, req.message)


@router.post("/invoke/{agent_type}", response_model=ChatResponse)
async def invoke_agent(
    agent_type: str,
    req: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Direct agent invocation — bypasses the orchestrator's intent classifier.
    Use when the system knows exactly which agent should handle a request
    (e.g., data uploaded → data_agent, gate review → dmaic_coach).
    """
    # Validate agent type
    try:
        target = AgentType(agent_type)
    except ValueError:
        valid = [a.value for a in AgentType]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent type '{agent_type}'. Valid types: {valid}",
        )

    context = _build_context(req)
    response = await orchestrator.invoke_specific(target, req.message, context)
    return _agent_response_to_chat(response, context, req.message)


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents(
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """List all registered AI agents and their capabilities."""
    agents = []
    for agent_type, agent in orchestrator._agents.items():
        agents.append(AgentInfo(
            agent_type=agent_type.value,
            model=agent.model,
            description=agent.__class__.__doc__ or "",
        ))
    return agents


# ---------------------------------------------------------------------------
# WebSocket — bi-directional real-time chat
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_chat(
    ws: WebSocket,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    WebSocket endpoint for real-time bi-directional AI chat.

    Client sends JSON messages:
        {"message": "...", "initiative_id": "...", "current_phase": "...", ...}

    Server streams back:
        {"type": "token", "content": "partial text"}
        {"type": "done", "full_content": "...", "suggestions": [...], "agent_type": "..."}
        {"type": "error", "detail": "..."}
    """
    await ws.accept()

    # Per-connection conversation state
    conversation_history: list[dict] = []
    conversation_summary: str | None = None

    try:
        while True:
            data = await ws.receive_json()

            # Build context from the incoming message
            context = AgentContext(
                user_id=UUID(data["user_id"]) if data.get("user_id") else None,
                user_name=data.get("user_name", ""),
                user_role=data.get("user_role", ""),
                initiative_id=UUID(data["initiative_id"]) if data.get("initiative_id") else None,
                initiative_title=data.get("initiative_title", ""),
                problem_statement=data.get("problem_statement", ""),
                desired_outcome=data.get("desired_outcome", ""),
                methodology=data.get("methodology", ""),
                current_phase=data.get("current_phase", ""),
                initiative_status=data.get("initiative_status", ""),
                initiative_priority=data.get("initiative_priority", ""),
                phase_artifacts=data.get("phase_artifacts", []),
                all_phases_status=data.get("all_phases_status", {}),
                dataset_profiles=data.get("dataset_profiles", []),
                analysis_results=data.get("analysis_results", []),
                metrics=data.get("metrics", []),
                conversation_history=conversation_history,
                conversation_summary=conversation_summary,
            )

            user_message = data.get("message", "")
            if not user_message:
                await ws.send_json({"type": "error", "detail": "Empty message"})
                continue

            # Stream the response
            full_content = ""
            async for chunk in orchestrator.stream_route(user_message, context):
                full_content += chunk
                await ws.send_json({"type": "token", "content": chunk})

            # Update conversation history for this connection
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": full_content})
            conversation_summary = context.conversation_summary

            # Send completion signal
            await ws.send_json({
                "type": "done",
                "full_content": full_content,
                "agent_type": "routed",
                "suggestions": [],
            })

    except WebSocketDisconnect:
        pass  # Client disconnected — clean exit
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass  # Connection already dead
