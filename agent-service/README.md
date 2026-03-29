# IoT-DevSim Agent Service

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688.svg)](https://fastapi.tiangolo.com/)
[![PydanticAI](https://img.shields.io/badge/PydanticAI-1.58-blueviolet.svg)](https://ai.pydantic.dev/)

AI-powered assistant for the IoT-DevSim platform. Provides a conversational interface (SSE streaming) that lets users manage connections, devices, datasets, projects, and transmissions through natural language.

## Architecture

```
┌─────────────┐  SSE   ┌──────────────────┐  HTTP  ┌──────────────┐
│  Frontend   │───────▶│  Agent Service   │───────▶│  API Service  │
│  (React)    │◀───────│  (FastAPI + AI)  │◀───────│  (FastAPI)    │
└─────────────┘        └──────────────────┘        └──────────────┘
                              │                           │
                              ▼                           ▼
                       ┌──────────┐               ┌───────────┐
                       │  Redis   │               │ PostgreSQL│
                       │  (DB 2)  │               │           │
                       └──────────┘               └───────────┘
```

### Security Pipeline (per request)

```
User Message → Rate Limiter → Prompt Guard → PydanticAI Agent → Output Filter → SSE Response
                  (429)         (block)        (LLM + tools)      (redact)       (stream)
```

## Quick Start

### With Docker (recommended)

```bash
# From the project root
docker compose --profile agent up -d

# Verify
curl http://localhost:8002/health
```

### Local Development

```bash
cd agent-service
pip install -r requirements.txt

# Set environment variables (or use .env in project root)
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o-mini
export LLM_API_KEY=sk-...
export JWT_SECRET_KEY=<same-as-api-service>
export API_SERVICE_URL=http://localhost:8000/api/v1

uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## LLM Provider Configuration

The agent supports multiple LLM providers via [PydanticAI](https://ai.pydantic.dev/).

### OpenAI (recommended)

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-proj-...
```

Supported models: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-...
```

### Ollama (local, no API key needed)

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Requires [Ollama](https://ollama.ai/) running locally with the model pulled:
```bash
ollama pull llama3.1:8b
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **LLM_PROVIDER** | ✅ | `ollama` | LLM provider: `openai`, `anthropic`, `ollama` |
| **LLM_MODEL** | ✅ | `llama3.1:8b` | Model name for the chosen provider |
| **LLM_API_KEY** | ⚠️ | *(empty)* | API key (required for openai/anthropic) |
| **LLM_TEMPERATURE** | ❌ | `0.3` | Sampling temperature (0.0–1.0) |
| **LLM_MAX_TOKENS** | ❌ | `1024` | Max tokens per response |
| **OLLAMA_BASE_URL** | ❌ | `http://host.docker.internal:11434` | Ollama server URL |
| **JWT_SECRET_KEY** | ✅ | *(insecure default)* | Must match api-service JWT secret |
| **JWT_ALGORITHM** | ❌ | `HS256` | JWT signing algorithm |
| **API_SERVICE_URL** | ✅ | `http://api-service:8000/api/v1` | Internal URL to api-service |
| **REDIS_URL** | ❌ | `redis://redis:6379/2` | Redis for session backup (DB 2) |
| **CORS_ORIGINS** | ❌ | `http://localhost:5173,...` | Allowed CORS origins |
| **AGENT_PORT** | ❌ | `8002` | Service port |
| **ENVIRONMENT** | ❌ | `development` | `development` or `production` |
| **LOG_LEVEL** | ❌ | `INFO` | Log level |
| **AGENT_MESSAGES_PER_MINUTE** | ❌ | `20` | Rate limit: messages per user per minute |
| **AGENT_ACTIONS_PER_SESSION** | ❌ | `50` | Rate limit: tool actions per session |
| **AGENT_CREATE_OPS_PER_HOUR** | ❌ | `30` | Rate limit: creation operations per hour |
| **SESSION_MAX_TURNS** | ❌ | `20` | Max conversation turns kept in memory |
| **SESSION_TTL_SECONDS** | ❌ | `1800` | Session timeout (30 minutes) |
| **SESSION_MAX_CONCURRENT** | ❌ | `500` | Max concurrent sessions in memory |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/agent/chat` | JWT | SSE streaming chat with the AI agent |
| `GET` | `/api/v1/agent/suggestions` | JWT | Contextual suggestions by page route |
| `GET` | `/api/v1/health` | — | Detailed health check (includes LLM status) |
| `GET` | `/health` | — | Simple health check (for Docker) |
| `GET` | `/docs` | — | OpenAPI/Swagger UI (development only) |
| `GET` | `/redoc` | — | ReDoc documentation (development only) |

### SSE Chat Protocol

**Request:**
```json
POST /api/v1/agent/chat
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "message": "Muéstrame mis conexiones",
  "session_id": "optional-uuid",
  "context": "/connections"
}
```

**SSE Response (streamed):**
```
data: {"type": "session", "session_id": "uuid-..."}

data: {"type": "content", "content": "Tienes 3 conexiones"}

data: {"type": "content", "content": " configuradas:\n- ..."}

data: [DONE]
```

**Event types:**
| Type | Description |
|------|-------------|
| `session` | Session ID acknowledgment (first event) |
| `content` | Text content chunk (streamed) |
| `tool_call` | Tool execution notification |
| `error` | Error message |
| `complete` | Stream complete |

## Agent Tools

The agent has access to 17 tools organized by domain:

| Domain | Tools | Description |
|--------|-------|-------------|
| **Connections** | `list_connections`, `create_connection`, `test_connection` | Manage IoT broker connections (MQTT, HTTP, Kafka) |
| **Datasets** | `list_datasets`, `create_dataset`, `preview_dataset`, `get_available_generators` | Generate and manage simulation datasets |
| **Devices** | `list_devices`, `create_device`, `get_device_status`, `link_dataset_to_device` | Virtual IoT device management |
| **Projects** | `list_projects`, `create_project`, `get_project_details`, `start_transmission`, `stop_transmission`, `get_project_stats` | Simulation project lifecycle |
| **Logs** | `query_transmission_logs`, `get_recent_errors` | Transmission log querying |
| **Analytics** | `get_performance_summary`, `analyze_transmission_trends` | Performance metrics and trend analysis |

## Security Model

Defense-in-depth architecture aligned with OWASP Top 10 for LLM Applications 2026.

### Layer 1-2: Authentication & Authorization
- JWT validation with `joserfc` (same secret as api-service)
- Token propagation to api-service on every internal call
- Session isolation: user A cannot access user B's session

### Layer 3: Input Sanitization (Prompt Guard)
- 22 regex patterns detecting prompt injection attempts
- Three threat levels: HIGH (blocked), MEDIUM (blocked), LOW (logged)
- Max message length: 2,000 characters
- Blocked messages receive a safe generic response

### Layer 4: Output Filtering
- 9 regex patterns sanitize every SSE chunk before sending
- Catches: JWT tokens, API keys, PEM private keys, certificates, passwords, connection strings, emails, AWS keys
- Sensitive data replaced with `[REDACTED]`

### Layer 5: Action Control
- **Forbidden actions**: `modify_user`, `change_password`, `delete_account`, `admin_operations`, `access_other_users`, `raw_database_query`, `modify_system_config`, `export_bulk_data`, `view_credentials`
- **Confirmation required**: `delete_connection`, `delete_device`, `delete_project`, `start_transmission`, `stop_transmission`, `bulk_create`
- Per-user rate limiting (configurable via env vars)

### Layer 6: Audit Logging
- All events logged via structlog (JSON in production)
- Message content hashed (SHA-256) — never stored raw
- 14 audit event types covering the full request lifecycle

### Session Memory
- Sliding window: 20 turns max
- TTL: 30 minutes (aligned with JWT expiration)
- LRU eviction: max 500 concurrent sessions
- User ID mismatch detection prevents cross-user access

## Testing

```bash
# Run all tests
cd agent-service
python -m pytest tests/ -v

# Run only security tests
python -m pytest tests/test_prompt_guard.py tests/test_output_filter.py tests/test_action_validator.py tests/test_audit_logger.py tests/test_security_e2e.py -v

# Run tool tests
python -m pytest tests/test_connection_tool.py tests/test_dataset_tool.py tests/test_device_tool.py tests/test_project_tool.py tests/test_log_query_tool.py tests/test_analytics_tool.py -v

# Inside Docker
docker exec iot-devsim-agent python -m pytest tests/ -v
```

## Project Structure

```
agent-service/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/
│   │   ├── config.py              # Pydantic-settings configuration
│   │   ├── logging.py             # Structlog setup (JSON prod / Console dev)
│   │   ├── security.py            # JWT validation with joserfc
│   │   └── llm_provider.py        # LLM provider factory + health check
│   ├── agent/
│   │   ├── deps.py                # AgentDeps dataclass
│   │   ├── orchestrator.py        # PydanticAI agent creation + tool registration
│   │   ├── prompts/
│   │   │   └── system_prompt.py   # System prompt with security rules
│   │   ├── memory/
│   │   │   └── session_memory.py  # Session memory manager (sliding window + TTL)
│   │   ├── security/
│   │   │   ├── prompt_guard.py    # Anti prompt-injection (Layer 3)
│   │   │   ├── output_filter.py   # Output sanitization (Layer 4)
│   │   │   ├── action_validator.py# Action classification + rate limiting (Layer 5)
│   │   │   └── audit_logger.py    # Structured audit logging (Layer 6)
│   │   └── tools/
│   │       ├── connection_tool.py # Connection management tools
│   │       ├── dataset_tool.py    # Dataset generation tools
│   │       ├── device_tool.py     # Device management tools
│   │       ├── project_tool.py    # Project lifecycle tools
│   │       ├── log_query_tool.py  # Log querying tools
│   │       └── analytics_tool.py  # Analytics and trends tools
│   ├── api/v1/
│   │   ├── router.py             # API router aggregation
│   │   └── endpoints/
│   │       ├── agent.py           # POST /chat (SSE), GET /suggestions
│   │       └── health.py          # GET /health (detailed)
│   ├── clients/
│   │   └── api_client.py         # Internal HTTP client to api-service
│   └── schemas/
│       └── agent.py              # Pydantic request/response models
├── tests/                         # 11 test files, ~120 test cases
├── Dockerfile                     # Multi-stage (development + production)
└── requirements.txt               # Python dependencies
```
