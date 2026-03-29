"""
Code Sandbox
Secure execution environment for LLM-generated Python code.
Validates AST, restricts imports/builtins, enforces timeout and output limits.
"""

import ast
import asyncio
import io
import math
import random
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import polars as pl
import structlog

logger = structlog.get_logger()

# ==================== AST Validation ====================

ALLOWED_IMPORTS = frozenset({"polars", "numpy", "datetime", "math", "random"})

FORBIDDEN_NAMES = frozenset({
    "open", "exec", "eval", "compile", "__import__", "input", "breakpoint",
    "exit", "quit", "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "type", "super",
    "classmethod", "staticmethod", "property",
})

FORBIDDEN_ATTRIBUTES = frozenset({
    "system", "popen", "connect", "urlopen", "request", "socket",
    "subprocess", "environ", "getenv", "putenv",
    "rmdir", "remove", "unlink", "rename", "mkdir", "makedirs",
    "write", "read", "readline", "readlines",
    "send", "recv", "bind", "listen", "accept",
    "__subclasses__", "__bases__", "__mro__", "__class__",
    "__globals__", "__builtins__", "__code__", "__import__",
})

MAX_ROWS = 100_000
MAX_COLUMNS = 50
EXECUTION_TIMEOUT_SECONDS = 30


class SandboxValidationError(Exception):
    """Raised when code fails AST security validation."""
    pass


class SandboxExecutionError(Exception):
    """Raised when code execution fails or times out."""
    pass


def validate_code(source: str) -> ast.Module:
    """
    Parse and validate Python source code against security rules.
    Returns the parsed AST if valid, raises SandboxValidationError otherwise.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise SandboxValidationError(f"Syntax error in generated code: {e}")

    for node in ast.walk(tree):
        # Block forbidden imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _check_import(node)

        # Block forbidden function calls
        if isinstance(node, ast.Call):
            _check_call(node)

        # Block forbidden attribute access
        if isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                raise SandboxValidationError(
                    f"Forbidden attribute access: '.{node.attr}'"
                )

        # Block forbidden name references
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise SandboxValidationError(
                    f"Forbidden name: '{node.id}'"
                )
            if node.id.startswith("__") and node.id.endswith("__"):
                raise SandboxValidationError(
                    f"Dunder access forbidden: '{node.id}'"
                )

    return tree


def _check_import(node: ast.AST) -> None:
    """Validate import statements against whitelist."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module not in ALLOWED_IMPORTS:
                raise SandboxValidationError(
                    f"Forbidden import: '{alias.name}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}"
                )
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            root_module = node.module.split(".")[0]
            if root_module not in ALLOWED_IMPORTS:
                raise SandboxValidationError(
                    f"Forbidden import from: '{node.module}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}"
                )


def _check_call(node: ast.Call) -> None:
    """Validate function calls against forbidden names."""
    if isinstance(node.func, ast.Name):
        if node.func.id in FORBIDDEN_NAMES:
            raise SandboxValidationError(
                f"Forbidden function call: '{node.func.id}()'"
            )
    elif isinstance(node.func, ast.Attribute):
        if node.func.attr in FORBIDDEN_ATTRIBUTES:
            raise SandboxValidationError(
                f"Forbidden method call: '.{node.func.attr}()'"
            )


# ==================== Restricted Namespace ====================

def _build_namespace() -> Dict[str, Any]:
    """Build the restricted namespace for code execution."""
    return {
        # Libraries
        "pl": pl,
        "np": np,
        "math": math,
        "random": random,
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
        # Minimal safe builtins
        "range": range,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "zip": zip,
        "enumerate": enumerate,
        "sorted": sorted,
        "reversed": reversed,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "map": map,
        "filter": filter,
        "print": lambda *a, **kw: None,  # no-op print
        "isinstance": isinstance,
        "None": None,
        "True": True,
        "False": False,
    }


# ==================== Execution ====================

def _execute_code_sync(source: str, namespace: Dict[str, Any]) -> pl.DataFrame:
    """
    Execute validated code in restricted namespace.
    The code must produce a variable named 'df' which is a polars DataFrame.
    """
    exec(compile(source, "<sandbox>", "exec"), {"__builtins__": {}}, namespace)

    df = namespace.get("df")
    if df is None:
        raise SandboxExecutionError(
            "Generated code must create a variable named 'df' "
            "containing a polars DataFrame."
        )

    if isinstance(df, pl.LazyFrame):
        df = df.collect()

    if not isinstance(df, pl.DataFrame):
        raise SandboxExecutionError(
            f"Variable 'df' must be a polars DataFrame, got {type(df).__name__}"
        )

    # Enforce limits
    if df.height > MAX_ROWS:
        raise SandboxExecutionError(
            f"DataFrame exceeds row limit: {df.height} > {MAX_ROWS}"
        )
    if df.width > MAX_COLUMNS:
        raise SandboxExecutionError(
            f"DataFrame exceeds column limit: {df.width} > {MAX_COLUMNS}"
        )
    if df.height == 0:
        raise SandboxExecutionError("Generated DataFrame is empty (0 rows).")

    return df


async def execute_sandboxed(source: str) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """
    Full pipeline: validate → build namespace → execute with timeout.
    Returns (DataFrame, metadata_dict).
    """
    # Step 1: AST validation
    validate_code(source)

    # Step 2: Execute in thread with timeout
    namespace = _build_namespace()
    try:
        df = await asyncio.wait_for(
            asyncio.to_thread(_execute_code_sync, source, namespace),
            timeout=EXECUTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise SandboxExecutionError(
            f"Code execution timed out after {EXECUTION_TIMEOUT_SECONDS}s"
        )
    except SandboxExecutionError:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.warning("Sandbox execution error", error=str(e), traceback=tb)
        raise SandboxExecutionError(f"Code execution failed: {e}")

    metadata = {
        "rows": df.height,
        "columns": df.width,
        "column_names": df.columns,
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
    }

    logger.info(
        "Sandbox execution successful",
        rows=df.height,
        columns=df.width,
    )

    return df, metadata
