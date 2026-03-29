"""
Project Tools
Agent tools for managing IoT simulation projects via api-service.
Includes transmission start/stop which require explicit user confirmation.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()


def _format_project_summary(p: dict) -> str:
    """Format a single project as a readable summary line."""
    name = p.get("name", "Sin nombre")
    status = p.get("transmission_status", "?")
    is_active = "✅" if p.get("is_active") else "❌"
    device_count = p.get("device_count", 0)
    pid = p.get("id", "")
    icon = {"idle": "⏸️", "running": "▶️", "paused": "⏯️", "stopped": "⏹️"}.get(
        status, "❓"
    )
    return f"- {is_active} {icon} **{name}** — {device_count} dispositivos — tx: {status} — `{pid}`"


def register_project_tools(agent):
    """Register all project tools on the agent."""

    @agent.tool
    async def list_projects(
        ctx: RunContext[AgentDeps],
        search: str = "",
    ) -> str:
        """List the user's simulation projects with optional search.

        Args:
            search: Optional search term to filter by name or description.
        """
        params: dict = {"limit": 50, "skip": 0}
        if search:
            params["search"] = search

        try:
            data = await ctx.deps.api_client.get(
                "/projects", ctx.deps.auth_token, params=params
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "No se encontraron proyectos."

            lines = [f"🗂️ **Proyectos** ({total} total):\n"]
            for p in items:
                lines.append(_format_project_summary(p))
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_projects failed", error=str(e))
            return f"Error al listar proyectos: {e}"

    @agent.tool
    async def create_project(
        ctx: RunContext[AgentDeps],
        name: str,
        device_ids: list[str] = [],
        description: str = "",
        tags: list[str] = [],
    ) -> str:
        """Create a new simulation project, optionally assigning devices.

        Args:
            name: Project name.
            device_ids: Optional list of device UUIDs to assign to the project.
            description: Optional description.
            tags: Optional list of tags.
        """
        payload: dict = {"name": name}
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags

        try:
            result = await ctx.deps.api_client.post(
                "/projects", ctx.deps.auth_token, data=payload
            )
            pid = result.get("id", "?")
            pname = result.get("name", name)

            # Assign devices if provided
            assigned = 0
            if device_ids:
                try:
                    await ctx.deps.api_client.post(
                        f"/projects/{pid}/devices",
                        ctx.deps.auth_token,
                        data={"device_ids": device_ids},
                    )
                    assigned = len(device_ids)
                except Exception as assign_err:
                    logger.warning(
                        "Device assignment failed during project creation",
                        project_id=pid,
                        error=str(assign_err),
                    )

            msg = f"✅ Proyecto creado: **{pname}** (`{pid}`)"
            if assigned:
                msg += f"\n- {assigned} dispositivo(s) asignado(s)"
            return msg
        except Exception as e:
            logger.error("create_project failed", error=str(e))
            return f"❌ Error al crear proyecto: {e}"

    @agent.tool
    async def get_project_details(
        ctx: RunContext[AgentDeps],
        project_id: str,
    ) -> str:
        """Get detailed information about a project including its devices.

        Args:
            project_id: UUID of the project.
        """
        try:
            project = await ctx.deps.api_client.get(
                f"/projects/{project_id}", ctx.deps.auth_token
            )
            devices_data = await ctx.deps.api_client.get(
                f"/projects/{project_id}/devices", ctx.deps.auth_token
            )

            name = project.get("name", "?")
            desc = project.get("description", "")
            tx_status = project.get("transmission_status", "?")
            is_active = "✅ Activo" if project.get("is_active") else "❌ Inactivo"
            devices = devices_data.get("devices", [])

            lines = [
                f"🗂️ **{name}** (`{project_id}`)",
                f"- Estado: {is_active}",
                f"- Transmisión: {tx_status}",
            ]
            if desc:
                lines.append(f"- Descripción: {desc}")
            lines.append(f"- Dispositivos asignados: {len(devices)}")
            for d in devices[:10]:
                dname = d.get("name", "?")
                dref = d.get("device_id", "?")
                has_ds = "📊" if d.get("has_dataset") else "⚠️ sin dataset"
                lines.append(f"  - **{dname}** (`{dref}`) {has_ds}")
            if len(devices) > 10:
                lines.append(f"  - ... y {len(devices) - 10} más")
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_project_details failed", error=str(e))
            return f"❌ Error al consultar proyecto: {e}"

    @agent.tool
    async def start_transmission(
        ctx: RunContext[AgentDeps],
        project_id: str,
        user_confirmed: bool = False,
    ) -> str:
        """Start data transmission for all devices in a project.

        ⚠️ IMPORTANT: This is a significant action. Only execute if the user has
        explicitly confirmed they want to start transmission. Set user_confirmed=True
        only when the user says 'sí', 'confirmar', 'adelante', or similar.

        Args:
            project_id: UUID of the project.
            user_confirmed: Must be True. Ask the user for confirmation first.
        """
        if not user_confirmed:
            return (
                "⚠️ **Confirmación requerida**: ¿Quieres iniciar la transmisión de datos "
                f"para el proyecto `{project_id}`? Esto enviará datos a las conexiones "
                "configuradas. Responde **sí** para confirmar."
            )

        try:
            result = await ctx.deps.api_client.post(
                f"/projects/{project_id}/transmissions/start",
                ctx.deps.auth_token,
            )
            status = result.get("status", "?")
            msg = result.get("message", "Transmisión iniciada")
            return f"▶️ {msg} — Estado: {status}"
        except Exception as e:
            logger.error("start_transmission failed", error=str(e))
            return f"❌ Error al iniciar transmisión: {e}"

    @agent.tool
    async def stop_transmission(
        ctx: RunContext[AgentDeps],
        project_id: str,
        user_confirmed: bool = False,
    ) -> str:
        """Stop all data transmissions for a project and reset row indices.

        ⚠️ IMPORTANT: This is a significant action. Only execute if the user has
        explicitly confirmed. Set user_confirmed=True only after user confirmation.

        Args:
            project_id: UUID of the project.
            user_confirmed: Must be True. Ask the user for confirmation first.
        """
        if not user_confirmed:
            return (
                "⚠️ **Confirmación requerida**: ¿Quieres detener la transmisión "
                f"del proyecto `{project_id}`? Se reiniciarán los índices de envío. "
                "Responde **sí** para confirmar."
            )

        try:
            result = await ctx.deps.api_client.post(
                f"/projects/{project_id}/transmissions/stop",
                ctx.deps.auth_token,
            )
            status = result.get("status", "?")
            msg = result.get("message", "Transmisión detenida")
            return f"⏹️ {msg} — Estado: {status}"
        except Exception as e:
            logger.error("stop_transmission failed", error=str(e))
            return f"❌ Error al detener transmisión: {e}"

    @agent.tool
    async def get_project_stats(
        ctx: RunContext[AgentDeps],
        project_id: str,
    ) -> str:
        """Get transmission statistics for a project.

        Args:
            project_id: UUID of the project.
        """
        try:
            stats = await ctx.deps.api_client.get(
                f"/projects/{project_id}/stats", ctx.deps.auth_token
            )
            total = stats.get("total_messages", 0)
            success = stats.get("success_count", 0)
            failed = stats.get("failure_count", 0)
            rate = (success / total * 100) if total > 0 else 0

            return (
                f"📊 **Estadísticas del proyecto** (`{project_id}`):\n"
                f"- Total mensajes: {total}\n"
                f"- Exitosos: {success} ({rate:.1f}%)\n"
                f"- Fallidos: {failed}\n"
            )
        except Exception as e:
            logger.error("get_project_stats failed", error=str(e))
            return f"❌ Error al obtener estadísticas: {e}"
