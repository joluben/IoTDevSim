"""
Connection Tools
Agent tools for managing IoT connections via api-service.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()

# Sensitive fields to strip from connection responses
_SENSITIVE_FIELDS = {
    "password", "secret", "private_key", "certificate", "cert",
    "api_key", "token", "credentials", "sasl_password",
}


def _sanitize_connection(conn: dict) -> dict:
    """Remove sensitive fields from a connection dict before returning to the agent."""
    if not isinstance(conn, dict):
        return conn
    sanitized = {}
    for key, value in conn.items():
        if key.lower() in _SENSITIVE_FIELDS:
            continue
        if key == "config" and isinstance(value, dict):
            sanitized[key] = {
                k: "***" if k.lower() in _SENSITIVE_FIELDS else v
                for k, v in value.items()
            }
        else:
            sanitized[key] = value
    return sanitized


def _format_connection_summary(conn: dict) -> str:
    """Format a single connection as a readable summary line."""
    name = conn.get("name", "Sin nombre")
    protocol = conn.get("protocol", "?")
    is_active = "✅" if conn.get("is_active") else "❌"
    test_status = conn.get("test_status", "unknown")
    conn_id = conn.get("id", "")
    return f"- {is_active} **{name}** ({protocol}) — test: {test_status} — `{conn_id}`"


def register_connection_tools(agent):
    """Register all connection tools on the agent."""

    @agent.tool
    async def list_connections(
        ctx: RunContext[AgentDeps],
        search: str = "",
        protocol: str = "",
    ) -> str:
        """List the user's IoT connections with optional search and protocol filter.

        Args:
            search: Optional search term to filter by name or description.
            protocol: Optional protocol filter (mqtt, http, https, kafka).
        """
        params = {"limit": 50, "skip": 0}
        if search:
            params["search"] = search
        if protocol:
            params["protocol"] = protocol

        try:
            data = await ctx.deps.api_client.get(
                "/connections", ctx.deps.auth_token, params=params
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "No se encontraron conexiones."

            lines = [f"📡 **Conexiones** ({total} total):\n"]
            for conn in items:
                lines.append(_format_connection_summary(_sanitize_connection(conn)))
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_connections failed", error=str(e))
            return f"Error al listar conexiones: {e}"

    @agent.tool
    async def create_connection(
        ctx: RunContext[AgentDeps],
        name: str,
        protocol: str,
        config: dict,
        description: str = "",
    ) -> str:
        """Create a new IoT connection.

        Args:
            name: Connection name.
            protocol: Protocol type — one of: mqtt, http, https, kafka.
            config: Protocol-specific configuration dict. For MQTT: {broker_url, port, topic}. For HTTP: {endpoint_url, method}. For Kafka: {bootstrap_servers, topic}.
            description: Optional description.
        """
        payload = {
            "name": name,
            "protocol": protocol,
            "config": config,
        }
        if description:
            payload["description"] = description

        try:
            result = await ctx.deps.api_client.post(
                "/connections", ctx.deps.auth_token, data=payload
            )
            conn_id = result.get("id", "?")
            conn_name = result.get("name", name)
            return f"✅ Conexión creada: **{conn_name}** (`{conn_id}`) — protocolo: {protocol}"
        except Exception as e:
            logger.error("create_connection failed", error=str(e))
            return f"❌ Error al crear conexión: {e}"

    @agent.tool
    async def test_connection(
        ctx: RunContext[AgentDeps],
        connection_id: str,
    ) -> str:
        """Test connectivity of an existing connection.

        Args:
            connection_id: UUID of the connection to test.
        """
        try:
            result = await ctx.deps.api_client.post(
                f"/connections/{connection_id}/test",
                ctx.deps.auth_token,
                data={"timeout": 10},
            )
            success = result.get("success", False)
            message = result.get("message", "")
            duration = result.get("duration_ms", 0)
            icon = "✅" if success else "❌"
            return f"{icon} Test de conexión: {message} ({duration}ms)"
        except Exception as e:
            logger.error("test_connection failed", error=str(e))
            return f"❌ Error al probar conexión: {e}"
