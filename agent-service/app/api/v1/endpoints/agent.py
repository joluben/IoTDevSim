"""
Agent chat and suggestions endpoints.
POST /api/v1/agent/chat  — SSE streaming chat
GET  /api/v1/agent/suggestions — contextual suggestions
"""

import asyncio
import json
from collections.abc import AsyncIterable
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic_ai import AgentStreamEvent, FunctionToolCallEvent, FunctionToolResultEvent, RunContext, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

from app.core.security import get_current_user, TokenPayload, security_scheme
from app.schemas.agent import (
    AgentChatRequest,
    AgentSuggestion,
    AgentSuggestionsResponse,
)
from app.agent.orchestrator import agent
from app.agent.deps import AgentDeps
from app.clients.api_client import internal_api_client
from app.agent.memory.session_memory import session_manager
from app.agent.security.prompt_guard import scan_message
from app.agent.security.output_filter import filter_output
from app.agent.security.action_validator import rate_limiter
from app.agent.security import audit_logger

logger = structlog.get_logger()

router = APIRouter(prefix="/agent", tags=["agent"])

# Contextual suggestions by page route
CONTEXTUAL_SUGGESTIONS = {
    "/dashboard": [
        AgentSuggestion(label="Estado de transmisiones", prompt="¿Cómo van mis transmisiones?"),
        AgentSuggestion(label="Crear proyecto", prompt="Quiero crear un nuevo proyecto de simulación"),
        AgentSuggestion(label="Errores recientes", prompt="Muéstrame los errores recientes de transmisión"),
    ],
    "/connections": [
        AgentSuggestion(label="Crear conexión MQTT", prompt="Ayúdame a crear una conexión MQTT"),
        AgentSuggestion(label="Probar conexión", prompt="Quiero probar una de mis conexiones"),
        AgentSuggestion(label="Listar conexiones", prompt="Muéstrame mis conexiones"),
    ],
    "/devices": [
        AgentSuggestion(label="Crear dispositivo", prompt="Quiero crear un nuevo dispositivo sensor"),
        AgentSuggestion(label="Dispositivos activos", prompt="¿Cuántos dispositivos activos tengo?"),
        AgentSuggestion(label="Vincular dataset", prompt="Quiero vincular un dataset a un dispositivo"),
    ],
    "/projects": [
        AgentSuggestion(label="Nuevo proyecto", prompt="Crear proyecto de simulación"),
        AgentSuggestion(label="Analizar transmisiones", prompt="Analiza las tendencias de transmisión de mi proyecto"),
        AgentSuggestion(label="Iniciar simulación", prompt="Quiero iniciar la transmisión de un proyecto"),
    ],
    "/datasets": [
        AgentSuggestion(label="Generar dataset", prompt="Quiero generar un dataset sintético de temperatura"),
        AgentSuggestion(label="Previsualizar", prompt="Previsualizar mi último dataset"),
        AgentSuggestion(label="Mis datasets", prompt="Muéstrame todos mis datasets"),
    ],
}

DEFAULT_SUGGESTIONS = [
    AgentSuggestion(label="¿Qué puedo hacer?", prompt="¿Qué puedo hacer con la plataforma IoTDevSim?"),
    AgentSuggestion(label="Crear conexión MQTT", prompt="Ayúdame a crear una conexión MQTT"),
    AgentSuggestion(label="Resumen de rendimiento", prompt="Dame un resumen de rendimiento de mis proyectos"),
]


@router.post("/chat")
async def agent_chat(
    request: AgentChatRequest,
    user: TokenPayload = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    """
    Chat with the AI agent via SSE streaming.
    Security pipeline: rate limit → prompt guard → agent → output filter → SSE.
    Each chunk is sent as a Server-Sent Event with JSON data.
    Final event is `data: [DONE]`.
    """
    # --- Layer 5a: Rate limiting ---
    if not rate_limiter.check_message_rate(user.sub):
        audit_logger.log_rate_limit_hit(user.sub, "messages_per_minute")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Has excedido el límite de mensajes. Espera un momento antes de enviar otro.",
        )

    # Get or create session memory
    session = session_manager.get_or_create(request.session_id, user.sub)

    # --- Audit: message received ---
    audit_logger.log_message_received(user.sub, session.session_id, request.message)

    # --- Layer 3: Prompt injection scan ---
    scan = scan_message(request.message)

    if scan.matched_patterns:
        audit_logger.log_prompt_injection(
            user_id=user.sub,
            session_id=session.session_id,
            threat_level=scan.threat_level.value,
            patterns=scan.matched_patterns,
            blocked=not scan.is_safe,
        )

    if not scan.is_safe:
        audit_logger.log_message_blocked(
            user_id=user.sub,
            session_id=session.session_id,
            reason="prompt_injection",
            threat_level=scan.threat_level.value,
            patterns=scan.matched_patterns,
        )
        # Return the safe rejection as a normal SSE response (not an error)
        async def blocked_stream():
            yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'content': scan.message})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            blocked_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    logger.info(
        "Agent chat request",
        user_id=user.sub,
        session_id=session.session_id,
        context=request.context,
        message_length=len(request.message),
    )

    # Build agent dependencies — propagate the raw JWT for api-service calls
    deps = AgentDeps(
        user_id=user.sub,
        auth_token=credentials.credentials,
        api_client=internal_api_client,
        session_memory=session,
        current_page=request.context,
    )

    # --- Usage limits to prevent infinite tool loops (OWASP LLM10) ---
    usage_limits = UsageLimits(
        request_limit=10,
        tool_calls_limit=25,
        response_tokens_limit=4096,
    )

    # Queue to bridge event_stream_handler tool events into the SSE generator
    tool_event_queue: asyncio.Queue[dict | None] = asyncio.Queue()
    # Map tool_call_id → tool_name so we can label completed events
    _tool_call_names: dict[str, str] = {}

    async def _event_stream_handler(
        ctx: RunContext[AgentDeps],
        event_stream: AsyncIterable[AgentStreamEvent],
    ) -> None:
        """Capture tool call / result events and push them into the queue."""
        async for event in event_stream:
            if isinstance(event, FunctionToolCallEvent):
                _tool_call_names[event.part.tool_call_id] = event.part.tool_name
                await tool_event_queue.put({
                    "type": "tool_call",
                    "tool_name": event.part.tool_name,
                    "status": "running",
                })
            elif isinstance(event, FunctionToolResultEvent):
                tool_name = _tool_call_names.get(event.tool_call_id, "unknown")
                await tool_event_queue.put({
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "status": "completed",
                })

    async def event_stream():
        """Generate SSE events from PydanticAI agent streaming with output filtering."""
        # Track if background draining is active
        drain_task: asyncio.Task | None = None

        async def _drain_queue_continuously():
            """Background task to continuously drain tool events from the queue."""
            while True:
                try:
                    # Wait for an event with timeout to allow clean cancellation
                    tool_evt = await asyncio.wait_for(tool_event_queue.get(), timeout=0.5)
                    if tool_evt:
                        # We can't yield directly from background task, so we use a sentinel
                        # Actually, we need to yield from the main generator
                        # Use a side channel or just let it queue up and drain in main loop
                        pass
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception:
                    break

        try:
            # Send session_id as first event
            yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"

            async with agent.run_stream(
                request.message,
                deps=deps,
                message_history=session.get_history(),
                usage_limits=usage_limits,
                event_stream_handler=_event_stream_handler,
            ) as result:
                # Use asyncio.gather or interleaved draining for better responsiveness
                text_iterator = result.stream_text(delta=True).__aiter__()
                chunk: str | None = None
                done = False

                while not done:
                    # Try to get next text chunk with timeout (allows interleaved draining)
                    try:
                        chunk = await asyncio.wait_for(
                            text_iterator.__anext__(),
                            timeout=0.1
                        )
                    except asyncio.TimeoutError:
                        chunk = None
                    except StopAsyncIteration:
                        done = True
                        chunk = None

                    # Drain ALL queued tool events before (and between) text chunks
                    while True:
                        try:
                            tool_evt = tool_event_queue.get_nowait()
                            if tool_evt:
                                yield f"data: {json.dumps(tool_evt)}\n\n"
                        except asyncio.QueueEmpty:
                            break

                    # Yield text chunk if we got one
                    if chunk is not None:
                        safe_chunk = filter_output(chunk)
                        yield f"data: {json.dumps({'type': 'content', 'content': safe_chunk})}\n\n"

                # Final drain after streaming ends
                while not tool_event_queue.empty():
                    try:
                        tool_evt = tool_event_queue.get_nowait()
                        if tool_evt:
                            yield f"data: {json.dumps(tool_evt)}\n\n"
                    except asyncio.QueueEmpty:
                        break

                # Save conversation to session memory
                session.add_turn(result.all_messages())

            yield "data: [DONE]\n\n"

        except UsageLimitExceeded as e:
            logger.warning(
                "Agent usage limit exceeded",
                user_id=user.sub,
                session_id=session.session_id,
                error=str(e),
            )
            error_msg = (
                "He alcanzado el límite de operaciones para esta solicitud. "
                "Intenta reformular tu pregunta de forma más concreta."
            )
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(
                "Agent chat error",
                user_id=user.sub,
                session_id=session.session_id,
                error=str(e),
            )
            error_msg = "Lo siento, ha ocurrido un error procesando tu solicitud. Inténtalo de nuevo."
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/suggestions", response_model=AgentSuggestionsResponse)
async def get_suggestions(
    context: str = Query(None, description="Current page route"),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get contextual suggestions based on the current page.
    """
    # Match exact route or find partial match
    suggestions = DEFAULT_SUGGESTIONS

    if context:
        # Try exact match first
        if context in CONTEXTUAL_SUGGESTIONS:
            suggestions = CONTEXTUAL_SUGGESTIONS[context]
        else:
            # Try partial match (e.g., /projects/123 matches /projects)
            for route, route_suggestions in CONTEXTUAL_SUGGESTIONS.items():
                if context.startswith(route):
                    suggestions = route_suggestions
                    break

    return AgentSuggestionsResponse(
        suggestions=suggestions,
        context=context,
    )
