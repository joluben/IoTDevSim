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
