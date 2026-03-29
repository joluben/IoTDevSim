"""
Analytics Tools
Agent tools for performance summaries, trend analysis, and basic anomaly detection.
Only aggregated data — never individual sensitive records.
"""

import structlog
from pydantic_ai import RunContext

from app.agent.deps import AgentDeps

logger = structlog.get_logger()


def register_analytics_tools(agent):
    """Register analytics tools on the agent."""

    @agent.tool
    async def get_performance_summary(
        ctx: RunContext[AgentDeps],
        project_id: str,
    ) -> str:
        """Get a performance summary for a project including success rate, latency, and volume trends.

        Args:
            project_id: UUID of the project to analyze.
        """
        try:
            stats = await ctx.deps.api_client.get(
                f"/projects/{project_id}/stats", ctx.deps.auth_token
            )

            total = stats.get("total_messages", 0)
            success = stats.get("success_count", 0)
            failed = stats.get("failure_count", 0)
            avg_latency = stats.get("avg_latency_ms", 0)
            min_latency = stats.get("min_latency_ms", 0)
            max_latency = stats.get("max_latency_ms", 0)

            success_rate = (success / total * 100) if total > 0 else 0
            failure_rate = (failed / total * 100) if total > 0 else 0

            # Determine health status
            if success_rate >= 99:
                health = "🟢 Excelente"
            elif success_rate >= 95:
                health = "🟡 Bueno"
            elif success_rate >= 80:
                health = "🟠 Degradado"
            else:
                health = "🔴 Crítico"

            lines = [
                f"📊 **Resumen de rendimiento** — {health}\n",
                f"**Volumen**",
                f"- Total mensajes: {total:,}",
                f"- Exitosos: {success:,} ({success_rate:.1f}%)",
                f"- Fallidos: {failed:,} ({failure_rate:.1f}%)",
                "",
                f"**Latencia**",
                f"- Promedio: {avg_latency:.0f}ms",
                f"- Mínima: {min_latency:.0f}ms",
                f"- Máxima: {max_latency:.0f}ms",
            ]

            # Basic anomaly hints
            anomalies = []
            if failure_rate > 5:
                anomalies.append(f"⚠️ Tasa de error alta ({failure_rate:.1f}%). Revisa los logs de error.")
            if avg_latency > 500:
                anomalies.append(f"⚠️ Latencia promedio elevada ({avg_latency:.0f}ms). Puede indicar problemas de red o broker.")
            if max_latency > 5000:
                anomalies.append(f"⚠️ Picos de latencia detectados (máx: {max_latency:.0f}ms).")

            if anomalies:
                lines.append("")
                lines.append("**⚠️ Anomalías detectadas**")
                for a in anomalies:
                    lines.append(f"- {a}")
            else:
                lines.append("")
                lines.append("✅ No se detectaron anomalías.")

            return "\n".join(lines)
        except Exception as e:
            logger.error("get_performance_summary failed", error=str(e))
            return f"❌ Error al obtener resumen de rendimiento: {e}"

    @agent.tool
    async def analyze_transmission_trends(
        ctx: RunContext[AgentDeps],
        project_id: str,
        device_id: str = "",
    ) -> str:
        """Analyze transmission trends for a project by looking at recent log history.

        Returns success/failure counts and latency distribution from recent logs.

        Args:
            project_id: UUID of the project.
            device_id: Optional UUID of a specific device to analyze.
        """
        params: dict = {"skip": 0, "limit": 200}
        if device_id:
            params["device_id"] = device_id

        try:
            data = await ctx.deps.api_client.get(
                f"/projects/{project_id}/history",
                ctx.deps.auth_token,
                params=params,
            )
            items = data.get("items", [])
            total_available = data.get("total", len(items))

            if not items:
                return "No hay suficientes datos para analizar tendencias."

            # Aggregate stats
            success_count = 0
            error_count = 0
            latencies = []
            devices_seen = set()
            protocols_seen = set()

            for entry in items:
                st = entry.get("status", "")
                if st == "success":
                    success_count += 1
                elif st in ("error", "failed", "timeout"):
                    error_count += 1

                lat = entry.get("latency_ms")
                if lat is not None and isinstance(lat, (int, float)):
                    latencies.append(lat)

                dev = entry.get("device_name", entry.get("device_ref", ""))
                if dev:
                    devices_seen.add(dev)

                proto = entry.get("protocol", "")
                if proto:
                    protocols_seen.add(proto)

            total_analyzed = success_count + error_count
            success_pct = (success_count / total_analyzed * 100) if total_analyzed > 0 else 0

            lines = [
                f"📈 **Análisis de tendencias** (últimas {len(items)} entradas de {total_available}):\n",
                f"**Resultado**",
                f"- Exitosos: {success_count} ({success_pct:.1f}%)",
                f"- Errores: {error_count}",
                f"- Dispositivos involucrados: {len(devices_seen)}",
                f"- Protocolos: {', '.join(protocols_seen) if protocols_seen else 'N/A'}",
            ]

            if latencies:
                avg_lat = sum(latencies) / len(latencies)
                sorted_lat = sorted(latencies)
                p50 = sorted_lat[len(sorted_lat) // 2]
                p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
                p95 = sorted_lat[p95_idx]

                lines.extend([
                    "",
                    f"**Latencia**",
                    f"- Promedio: {avg_lat:.0f}ms",
                    f"- P50: {p50:.0f}ms",
                    f"- P95: {p95:.0f}ms",
                    f"- Rango: {sorted_lat[0]:.0f}ms — {sorted_lat[-1]:.0f}ms",
                ])

                # Simple anomaly: check for high variance
                if len(latencies) > 5:
                    mean = avg_lat
                    variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
                    std_dev = variance ** 0.5
                    if std_dev > mean * 0.5:
                        lines.append(f"\n⚠️ Alta variabilidad en latencia (σ={std_dev:.0f}ms). "
                                     "Posibles problemas intermitentes de red.")

            return "\n".join(lines)
        except Exception as e:
            logger.error("analyze_transmission_trends failed", error=str(e))
            return f"❌ Error al analizar tendencias: {e}"
