"""
LLM-Assisted Dataset Generator
Translates natural language descriptions into Polars code via LLM,
executes in sandbox, and uploads the resulting CSV to api-service.

Uses a dedicated PydanticAI Agent (not the main orchestrator) for code
generation, so it respects the configured LLM_PROVIDER (Ollama, OpenAI,
Anthropic) without hard-coding any specific SDK.
"""

import io
import structlog
from typing import Optional, Tuple, Dict, Any

import polars as pl
from pydantic_ai import Agent, UsageLimits, RunContext

from app.agent.deps import AgentDeps
from app.core.config import settings
from app.agent.tools.code_sandbox import (
    execute_sandboxed,
    SandboxValidationError,
    SandboxExecutionError,
)

logger = structlog.get_logger()

# ==================== System Prompt ====================

CODEGEN_SYSTEM_PROMPT = """You are an expert Python data engineer specializing in IoT synthetic data generation.
Your task is to generate Python code that creates a realistic dataset based on the user's description.

RULES:
1. You MUST use Polars (`pl`) for DataFrame creation — NOT pandas.
2. The final result MUST be a variable named `df` containing a `pl.DataFrame`.
3. Available libraries (pre-imported in namespace):
   - `pl` (polars)
   - `np` (numpy)
   - `math`, `random`
   - `datetime`, `timedelta`, `timezone` (from datetime module)
4. DO NOT import anything — all libraries are already available.
5. DO NOT use `open()`, `exec()`, `eval()`, file I/O, or network calls.
6. DO NOT generate real personal data (PII): no real names, emails, addresses, or phone numbers.
7. Generate realistic patterns:
   - Time series data should have realistic temporal patterns (daily cycles, weekly patterns, seasonal trends).
   - Sensor data should include realistic noise, drift, and occasional anomalies.
   - Use domain knowledge to create plausible value ranges and distributions.
8. Column names should be lowercase with underscores (snake_case).
9. Include a `timestamp` column as the first column using `datetime` objects.
10. The code should be clean and efficient.

OUTPUT: Return ONLY the Python code block, no explanations, no markdown fences.
The code must create a variable `df` as a `pl.DataFrame`.

Example for a temperature sensor:
```
timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(720)]
base_temp = 22.0
temps = [base_temp + 3 * math.sin(2 * math.pi * i / 24) + random.gauss(0, 0.5) for i in range(720)]
df = pl.DataFrame({"timestamp": timestamps, "temperature_c": temps})
```
"""


# ==================== Lazy Agent Singleton ====================

_codegen_agent: Optional[Agent[None, str]] = None


def _get_codegen_agent() -> Agent[None, str]:
    """Create or return the cached code-generation PydanticAI Agent.

    Uses the same LLM provider/model configured in settings, so it works
    with Ollama, OpenAI, and Anthropic without any SDK-specific code.
    """
    global _codegen_agent
    if _codegen_agent is None:
        _codegen_agent = Agent(
            settings.llm_model_string,
            system_prompt=CODEGEN_SYSTEM_PROMPT,
            retries=1,
        )
        logger.info(
            "Codegen agent created",
            model=settings.llm_model_string,
            provider=settings.LLM_PROVIDER,
        )
    return _codegen_agent


# ==================== Code Extraction ====================

def _extract_code_block(llm_response: str) -> str:
    """Extract Python code from LLM response, stripping markdown fences if present."""
    text = llm_response.strip()

    # Try to extract from ```python ... ``` or ``` ... ```
    if "```" in text:
        parts = text.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:  # odd parts are inside fences
                code = part.strip()
                if code.startswith("python"):
                    code = code[len("python"):].strip()
                elif code.startswith("py"):
                    code = code[len("py"):].strip()
                return code

    # No fences — treat entire response as code
    return text


# ==================== DataFrame to CSV ====================

def dataframe_to_csv_bytes(df: pl.DataFrame) -> bytes:
    """Convert a Polars DataFrame to CSV bytes."""
    buf = io.BytesIO()
    df.write_csv(buf)
    return buf.getvalue()


def dataframe_preview(df: pl.DataFrame, max_rows: int = 10) -> str:
    """Format first N rows of a DataFrame as a markdown table."""
    preview = df.head(max_rows)
    cols = preview.columns
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows_str = []
    for row in preview.iter_rows():
        vals = [str(v) for v in row]
        rows_str.append("| " + " | ".join(vals) + " |")

    lines = [
        f"📊 **Preview** ({df.height} filas, {df.width} columnas):\n",
        header,
        separator,
    ] + rows_str

    return "\n".join(lines)


# ==================== Main Generator ====================

async def generate_dataset_with_llm(
    ctx: RunContext[AgentDeps],
    description: str,
    dataset_name: str,
) -> Tuple[str, Optional[str]]:
    """
    Full pipeline: description → LLM code generation → sandbox execution → upload.

    Uses a dedicated PydanticAI Agent so it works with the configured
    LLM_PROVIDER (Ollama, OpenAI, Anthropic) instead of only OpenAI.

    Returns (success_message, error_message). One of them will be None.
    """
    logger.info(
        "LLM dataset generation started",
        description=description[:100],
        dataset_name=dataset_name,
    )

    # Step 1: Call LLM to generate code via PydanticAI (multi-provider)
    try:
        codegen = _get_codegen_agent()
        prompt = (
            f"Generate a Polars DataFrame for this IoT dataset:\n\n"
            f"Name: {dataset_name}\n"
            f"Description: {description}\n\n"
            f"Create the `df` variable with realistic synthetic data."
        )
        result = await codegen.run(
            prompt,
            usage_limits=UsageLimits(
                request_limit=3,
                response_tokens_limit=2048,
            ),
        )

        raw_code = result.output
        if not raw_code:
            return None, "❌ El LLM no generó código."

        code = _extract_code_block(raw_code)
        logger.info("LLM code generated", code_length=len(code))

    except Exception as e:
        logger.error("LLM code generation failed", error=str(e))
        return None, f"❌ Error al generar código con LLM: {e}"

    # Step 2: Execute in sandbox
    try:
        df, metadata = await execute_sandboxed(code)
    except SandboxValidationError as e:
        logger.warning("Sandbox validation failed", error=str(e))
        return None, f"❌ Código generado no pasó validación de seguridad: {e}"
    except SandboxExecutionError as e:
        logger.warning("Sandbox execution failed", error=str(e))
        return None, f"❌ Error al ejecutar código generado: {e}"

    # Step 3: Convert to CSV and upload
    try:
        csv_bytes = dataframe_to_csv_bytes(df)
        logger.info("CSV generated", size_bytes=len(csv_bytes))

        result = await _upload_csv(
            ctx.deps.api_client,
            ctx.deps.auth_token,
            csv_bytes,
            dataset_name,
            description,
        )

        ds_id = result.get("id", "?")
        rows = result.get("row_count", metadata["rows"])
        cols = result.get("column_count", metadata["columns"])

        preview = dataframe_preview(df)

        success_msg = (
            f"✅ Dataset generado con IA: **{dataset_name}** (`{ds_id}`)\n"
            f"- Filas: {rows}\n"
            f"- Columnas: {cols}\n"
            f"- Columnas: {', '.join(metadata['column_names'])}\n\n"
            f"{preview}"
        )

        return success_msg, None

    except Exception as e:
        logger.error("CSV upload failed", error=str(e))
        return None, f"❌ Error al subir dataset: {e}"


async def _upload_csv(
    api_client,
    auth_token: str,
    csv_bytes: bytes,
    name: str,
    description: str,
) -> Dict[str, Any]:
    """Upload CSV bytes to api-service via multipart form."""
    import httpx

    base_url = settings.API_SERVICE_URL.rstrip("/")
    url = f"{base_url}/datasets/upload"

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0)) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("dataset.csv", csv_bytes, "text/csv")},
            data={
                "name": name,
                "description": description or "",
                "tags": '["llm_assisted", "synthetic"]',
                "has_header": "true",
                "delimiter": ",",
                "encoding": "utf-8",
            },
        )
        response.raise_for_status()
        return response.json()


# ==================== Tool Registration ====================

def register_llm_dataset_tools(agent):
    """Register the LLM-assisted dataset generation tool."""

    @agent.tool
    async def create_dataset_with_ai(
        ctx: RunContext[AgentDeps],
        description: str,
        dataset_name: str,
    ) -> str:
        """Generate a custom IoT dataset using AI. The AI writes Python code to create
        realistic synthetic data based on a natural language description. Use this when
        the user wants a dataset with specific patterns, domain knowledge, or custom
        time series that don't fit the standard generators (temperature, equipment, etc.).

        Args:
            description: Detailed natural language description of the desired dataset.
                Include: what is being measured, time range, frequency, realistic patterns,
                units, and any domain-specific behavior. More detail = better results.
                Example: "Water meter readings for a 2-adult household, hourly for 2 months,
                with higher consumption in morning and evening, weekend variations."
            dataset_name: Name for the dataset (must be unique).
        """
        success, error = await generate_dataset_with_llm(ctx, description, dataset_name)
        if error:
            return error
        return success
