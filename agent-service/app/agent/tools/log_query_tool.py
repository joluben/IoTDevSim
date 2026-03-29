"""
Log Query Tools
Agent tools for querying transmission logs via api-service.
Restrictions: only user's logs, max 100 results, no message_content exposed.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()

# Fields to exclude from log entries (raw payloads, message content)
_EXCLUDED_LOG_FIELDS = {"message_content", "payload", "raw_message", "body"}

MAX_LOG_RESULTS = 100


def _sanitize_log_entry(entry: dict) -> dict:
    """Remove sensitive payload data from log entries."""
    return {k: v for k, v in entry.items() if k.lower() not in _EXCLUDED_LOG_FIELDS}


def _format_log_entry(entry: dict) -> str:
    """Format a single log entry as a readable line."""
    ts = entry.get("timestamp", "?")
    device = entry.get("device_name", entry.get("device_ref", "?"))
    status = entry.get("status", "?")
    protocol = entry.get("protocol", "?")
    latency = entry.get("latency_ms", "?")
    error = entry.get("error_message", "")
    icon = "✅" if status == "success" else "❌" if status in ("error", "failed") else "⚠️"
    line = f"- {icon} `{ts}` — **{device}** ({protocol}) — {status}"
    if latency and latency != "?":
        line += f" — {latency}ms"
    if error:
        line += f" — _{error}_"
    return line


def register_log_query_tools(agent):
    """Register log query tools on the agent."""

    @agent.tool
    async def query_transmission_logs(
        ctx: RunContext[AgentDeps],
        project_id: str,
        device_id: str = "",
        status: str = "",
        limit: int = 20,
    ) -> str:
        """Query transmission logs for a project with optional filters.

        Args:
            project_id: UUID of the project to query logs for.
            device_id: Optional UUID of a specific device to filter by.
            status: Optional status filter (success, error, failed, timeout).
            limit: Maximum number of log entries to return (max 100, default 20).
        """
        if limit > MAX_LOG_RESULTS:
            limit = MAX_LOG_RESULTS

        params: dict = {"skip": 0, "limit": limit}
        if device_id:
            params["device_id"] = device_id
        if status:
            params["status"] = status

        try:
            data = await ctx.deps.api_client.get(
                f"/projects/{project_id}/history",
                ctx.deps.auth_token,
                params=params,
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "No se encontraron logs de transmisión con esos filtros."

            lines = [f"📋 **Logs de transmisión** ({len(items)} de {total} total):\n"]
            for entry in items:
                lines.append(_format_log_entry(_sanitize_log_entry(entry)))

            if total > len(items):
                lines.append(f"\n_Mostrando {len(items)} de {total}. Usa filtros para refinar._")

            return "\n".join(lines)
        except Exception as e:
            logger.error("query_transmission_logs failed", error=str(e))
            return f"Error al consultar logs: {e}"

    @agent.tool
    async def get_recent_errors(
        ctx: RunContext[AgentDeps],
        project_id: str,
        limit: int = 10,
    ) -> str:
        """Get recent transmission errors for a project. Shortcut for querying logs with status=error.

        Args:
            project_id: UUID of the project.
            limit: Maximum number of error entries (max 50, default 10).
        """
        if limit > 50:
            limit = 50

        try:
            data = await ctx.deps.api_client.get(
                f"/projects/{project_id}/history",
                ctx.deps.auth_token,
                params={"status": "error", "skip": 0, "limit": limit},
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "✅ No hay errores recientes de transmisión. ¡Todo parece funcionar correctamente!"

            lines = [f"❌ **Errores recientes** ({total} total):\n"]
            for entry in items:
                lines.append(_format_log_entry(_sanitize_log_entry(entry)))

            return "\n".join(lines)
        except Exception as e:
            logger.error("get_recent_errors failed", error=str(e))
            return f"Error al consultar errores: {e}"
