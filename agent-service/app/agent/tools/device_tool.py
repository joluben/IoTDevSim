"""
Device Tools
Agent tools for managing IoT devices via api-service.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()

# Fields to strip from device responses (internal tokens, etc.)
_HIDDEN_FIELDS = {"internal_token", "auth_token", "secret"}


def _sanitize_device(device: dict) -> dict:
    """Remove internal tokens from device data."""
    return {k: v for k, v in device.items() if k.lower() not in _HIDDEN_FIELDS}


def _format_device_summary(d: dict) -> str:
    """Format a single device as a readable summary line."""
    name = d.get("name", "Sin nombre")
    device_id = d.get("device_id", "?")
    device_type = d.get("device_type", "?")
    is_active = "✅" if d.get("is_active") else "❌"
    status = d.get("status", "?")
    has_dataset = "📊" if d.get("has_dataset") else "⚠️ sin dataset"
    uuid = d.get("id", "")
    return f"- {is_active} **{name}** ({device_type}, ref: `{device_id}`) — {status} {has_dataset} — `{uuid}`"


def register_device_tools(agent):
    """Register all device tools on the agent."""

    @agent.tool
    async def list_devices(
        ctx: RunContext[AgentDeps],
        search: str = "",
        device_type: str = "",
        connection_id: str = "",
        project_id: str = "",
    ) -> str:
        """List the user's IoT devices with optional filters.

        Args:
            search: Optional search term to filter by name, device_id, or description.
            device_type: Optional filter by device type (sensor or datalogger).
            connection_id: Optional UUID to filter devices by connection.
            project_id: Optional UUID to filter devices by project.
        """
        params: dict = {"limit": 50, "skip": 0}
        if search:
            params["search"] = search
        if device_type:
            params["device_type"] = device_type
        if connection_id:
            params["connection_id"] = connection_id
        if project_id:
            params["project_id"] = project_id

        try:
            data = await ctx.deps.api_client.get(
                "/devices", ctx.deps.auth_token, params=params
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "No se encontraron dispositivos."

            lines = [f"📱 **Dispositivos** ({total} total):\n"]
            for d in items:
                lines.append(_format_device_summary(_sanitize_device(d)))
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_devices failed", error=str(e))
            return f"Error al listar dispositivos: {e}"

    @agent.tool
    async def create_device(
        ctx: RunContext[AgentDeps],
        name: str,
        device_type: str = "sensor",
        connection_id: str = "",
        description: str = "",
        tags: list[str] = [],
    ) -> str:
        """Create a new IoT device.

        Args:
            name: Device name.
            device_type: Device type — 'sensor' (single dataset) or 'datalogger' (multiple datasets).
            connection_id: Optional UUID of the connection to associate.
            description: Optional description.
            tags: Optional list of tags.
        """
        payload: dict = {
            "name": name,
            "device_type": device_type,
        }
        if connection_id:
            payload["connection_id"] = connection_id
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags

        try:
            result = await ctx.deps.api_client.post(
                "/devices", ctx.deps.auth_token, data=payload
            )
            dev_id = result.get("id", "?")
            dev_ref = result.get("device_id", "?")
            dev_name = result.get("name", name)
            return (
                f"✅ Dispositivo creado: **{dev_name}**\n"
                f"- UUID: `{dev_id}`\n"
                f"- Referencia: `{dev_ref}`\n"
                f"- Tipo: {device_type}"
            )
        except Exception as e:
            logger.error("create_device failed", error=str(e))
            return f"❌ Error al crear dispositivo: {e}"

    @agent.tool
    async def get_device_status(
        ctx: RunContext[AgentDeps],
        device_id: str,
    ) -> str:
        """Get the current status and details of a device.

        Args:
            device_id: UUID of the device to query.
        """
        try:
            data = await ctx.deps.api_client.get(
                f"/devices/{device_id}", ctx.deps.auth_token
            )
            d = _sanitize_device(data)
            name = d.get("name", "?")
            ref = d.get("device_id", "?")
            dtype = d.get("device_type", "?")
            is_active = "✅ Activo" if d.get("is_active") else "❌ Inactivo"
            status = d.get("status", "?")
            tx_enabled = "✅" if d.get("transmission_enabled") else "❌"
            ds_count = d.get("dataset_count", 0)
            conn_id = d.get("connection_id", "Sin conexión")

            return (
                f"📱 **{name}** (ref: `{ref}`)\n"
                f"- Tipo: {dtype}\n"
                f"- Estado: {is_active} — {status}\n"
                f"- Transmisión habilitada: {tx_enabled}\n"
                f"- Datasets vinculados: {ds_count}\n"
                f"- Conexión: `{conn_id}`"
            )
        except Exception as e:
            logger.error("get_device_status failed", error=str(e))
            return f"❌ Error al consultar dispositivo: {e}"

    @agent.tool
    async def link_dataset_to_device(
        ctx: RunContext[AgentDeps],
        device_id: str,
        dataset_id: str,
    ) -> str:
        """Link a dataset to a device so it can transmit data.

        Args:
            device_id: UUID of the device.
            dataset_id: UUID of the dataset to link.
        """
        try:
            result = await ctx.deps.api_client.post(
                f"/devices/{device_id}/datasets",
                ctx.deps.auth_token,
                data={"dataset_id": dataset_id},
            )
            return f"✅ Dataset `{dataset_id}` vinculado al dispositivo `{device_id}`."
        except Exception as e:
            logger.error("link_dataset_to_device failed", error=str(e))
            return f"❌ Error al vincular dataset: {e}"
