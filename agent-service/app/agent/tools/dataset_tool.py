"""
Dataset Tools
Agent tools for managing IoT datasets via api-service.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()


def _format_dataset_summary(ds: dict) -> str:
    """Format a single dataset as a readable summary line."""
    name = ds.get("name", "Sin nombre")
    source = ds.get("source", "?")
    status = ds.get("status", "?")
    rows = ds.get("row_count", "?")
    cols = ds.get("column_count", "?")
    ds_id = ds.get("id", "")
    icon = "✅" if status == "ready" else "⏳" if status == "processing" else "📄"
    return f"- {icon} **{name}** ({source}, {rows} filas, {cols} cols) — `{ds_id}`"


def register_dataset_tools(agent):
    """Register all dataset tools on the agent."""

    @agent.tool
    async def get_dataset_details(
        ctx: RunContext[AgentDeps],
        dataset_id: str,
    ) -> str:
        """Get detailed information about a specific dataset including columns.

        Args:
            dataset_id: UUID of the dataset.
        """
        try:
            data = await ctx.deps.api_client.get(
                f"/datasets/{dataset_id}", ctx.deps.auth_token
            )
            name = data.get("name", "Sin nombre")
            ds_id = data.get("id", dataset_id)
            desc = data.get("description", "Sin descripción")
            status = data.get("status", "?")
            source = data.get("source", "?")
            rows = data.get("row_count", "?")
            cols = data.get("column_count", "?")
            tags = data.get("tags", [])
            created = data.get("created_at", "?")
            updated = data.get("updated_at", "?")

            lines = [
                f"📊 **{name}** (`{ds_id}`)",
                f"- **Estado**: {status}",
                f"- **Fuente**: {source}",
                f"- **Filas**: {rows} | **Columnas**: {cols}",
                f"- **Descripción**: {desc}",
            ]
            if tags:
                lines.append(f"- **Etiquetas**: {', '.join(tags)}")
            lines.extend([
                f"- **Creado**: {created}",
                f"- **Actualizado**: {updated}",
            ])

            # Include column details
            columns = data.get("columns", [])
            if columns:
                lines.append("\n**Columnas**:")
                for col in columns:
                    col_name = col.get("name", "?")
                    col_type = col.get("data_type", "?")
                    lines.append(f"  - {col_name} ({col_type})")

            return "\n".join(lines)
        except Exception as e:
            logger.error("get_dataset_details failed", error=str(e))
            return f"❌ Error al obtener detalles del dataset: {e}"

    @agent.tool
    async def list_datasets(
        ctx: RunContext[AgentDeps],
        search: str = "",
    ) -> str:
        """List the user's datasets with optional search filter.

        Args:
            search: Optional search term to filter by name or description.
        """
        params = {"limit": 50, "skip": 0}
        if search:
            params["search"] = search

        try:
            data = await ctx.deps.api_client.get(
                "/datasets", ctx.deps.auth_token, params=params
            )
            items = data.get("items", [])
            total = data.get("total", len(items))

            if not items:
                return "No se encontraron datasets."

            lines = [f"📊 **Datasets** ({total} total):\n"]
            for ds in items:
                lines.append(_format_dataset_summary(ds))
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_datasets failed", error=str(e))
            return f"Error al listar datasets: {e}"

    @agent.tool
    async def create_dataset(
        ctx: RunContext[AgentDeps],
        name: str,
        generator_type: str,
        generator_config: dict,
        description: str = "",
        tags: list[str] = [],
    ) -> str:
        """Generate a synthetic IoT dataset.

        Args:
            name: Dataset name.
            generator_type: Generator type — one of: temperature, equipment, environmental, fleet, custom.
            generator_config: Generator-specific configuration. For 'custom' generator: {"columns": [{"name": "col_name", "type": "integer|float|string|boolean|datetime|timestamp", "config": {"min": 0, "max": 100}}], "num_rows": 1000}. For 'temperature': {"sensor_count": 5, "duration_days": 7}. For 'equipment': {"equipment_types": ["pump","motor"], "equipment_count": 10}. For 'environmental': {"location_count": 3, "parameters": ["temperature","humidity"]}. For 'fleet': {"vehicle_count": 5}.
            description: Optional description.
            tags: Optional list of tags.
        """
        payload = {
            "name": name,
            "generator_type": generator_type,
            "generator_config": generator_config,
        }
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags

        try:
            result = await ctx.deps.api_client.post(
                "/datasets/generate", ctx.deps.auth_token, data=payload
            )
            ds_id = result.get("id", "?")
            ds_name = result.get("name", name)
            rows = result.get("row_count", "?")
            cols = result.get("column_count", "?")
            return (
                f"✅ Dataset generado: **{ds_name}** (`{ds_id}`)\n"
                f"- Filas: {rows}\n"
                f"- Columnas: {cols}\n"
                f"- Generador: {generator_type}"
            )
        except Exception as e:
            logger.error("create_dataset failed", error=str(e))
            return f"❌ Error al generar dataset: {e}"

    @agent.tool
    async def preview_dataset(
        ctx: RunContext[AgentDeps],
        dataset_id: str,
    ) -> str:
        """Preview the first rows and column info of a dataset.

        Args:
            dataset_id: UUID of the dataset to preview.
        """
        try:
            data = await ctx.deps.api_client.get(
                f"/datasets/{dataset_id}/preview",
                ctx.deps.auth_token,
                params={"limit": 10},
            )

            columns = data.get("columns", [])
            rows = data.get("rows", [])
            total_rows = data.get("total_rows", "?")

            lines = [f"📊 **Preview** (mostrando {len(rows)} de {total_rows} filas):\n"]

            # Column header
            if columns:
                col_names = [c.get("name", "?") for c in columns]
                lines.append("**Columnas**: " + ", ".join(col_names))
                lines.append("")

            # Data rows as markdown table (max 10)
            if rows and columns:
                col_keys = [c.get("name", "") for c in columns]
                header = "| " + " | ".join(col_keys) + " |"
                separator = "| " + " | ".join(["---"] * len(col_keys)) + " |"
                lines.append(header)
                lines.append(separator)
                for row in rows[:10]:
                    vals = [str(row.get(k, "")) for k in col_keys]
                    lines.append("| " + " | ".join(vals) + " |")

            return "\n".join(lines)
        except Exception as e:
            logger.error("preview_dataset failed", error=str(e))
            return f"❌ Error al previsualizar dataset: {e}"

    @agent.tool
    async def get_available_generators(
        ctx: RunContext[AgentDeps],
    ) -> str:
        """Get the list of available synthetic data generators and their required configuration."""
        try:
            generators = await ctx.deps.api_client.get(
                "/datasets/generators", ctx.deps.auth_token
            )
            if not generators:
                return "No hay generadores disponibles."

            lines = ["🔧 **Generadores disponibles**:\n"]
            for gen in generators:
                name = gen.get("name", "?")
                desc = gen.get("description", "")
                lines.append(f"- **{name}**: {desc}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_available_generators failed", error=str(e))
            return f"Error al obtener generadores: {e}"

    @agent.tool
    async def update_dataset_metadata(
        ctx: RunContext[AgentDeps],
        dataset_id: str,
        name: str = "",
        description: str = "",
        tags: list[str] = [],
    ) -> str:
        """Update a dataset's metadata (name, description, tags). Does NOT modify data content.

        Args:
            dataset_id: UUID of the dataset to update.
            name: New name for the dataset (optional).
            description: New description (optional).
            tags: New list of tags (optional, replaces existing tags).
        """
        payload: dict[str, str | list[str]] = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags

        if not payload:
            return "⚠️ No se proporcionaron campos para actualizar."

        try:
            result = await ctx.deps.api_client.put(
                f"/datasets/{dataset_id}", ctx.deps.auth_token, data=payload
            )
            ds_name = result.get("name", "?")
            ds_id = result.get("id", dataset_id)
            return f"✅ Dataset actualizado: **{ds_name}** (`{ds_id}`)"
        except Exception as e:
            logger.error("update_dataset_metadata failed", error=str(e))
            return f"❌ Error al actualizar dataset: {e}"

    @agent.tool
    async def delete_dataset(
        ctx: RunContext[AgentDeps],
        dataset_id: str,
        hard_delete: bool = False,
    ) -> str:
        """Delete a dataset (soft delete by default, or hard delete).

        Args:
            dataset_id: UUID of the dataset to delete.
            hard_delete: If True, permanently deletes the dataset and its data file.
        """
        try:
            await ctx.deps.api_client.delete(
                f"/datasets/{dataset_id}",
                ctx.deps.auth_token,
                params={"hard_delete": hard_delete} if hard_delete else {}
            )
            delete_type = "eliminado permanentemente" if hard_delete else "marcado como eliminado"
            return f"✅ Dataset `{dataset_id}` {delete_type}."
        except Exception as e:
            logger.error("delete_dataset failed", error=str(e))
            return f"❌ Error al eliminar dataset: {e}"
