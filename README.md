# IoTDevSim

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A comprehensive IoT device simulation and management platform for testing and development of IoT systems. Simulate thousands of IoT devices, manage connections across multiple protocols, and monitor data transmission in real-time.

## Features

- **Multi-Protocol Support**: MQTT (TCP/WebSocket/TLS), HTTP/HTTPS webhooks, Kafka
- **Connection Pooling**: Efficient connection reuse per device connection to minimize overhead
- **Circuit Breaker Pattern**: Automatic failure detection with exponential backoff recovery
- **Resilient Error Handling**: Retry logic with exponential backoff, detailed error logging, and automatic device status updates
- **Real-time Monitoring**: Live dashboard with transmission logs, performance metrics, and system health
- **Device Simulation**: Create virtual IoT devices with customizable payloads and transmission patterns
- **Project Organization**: Group devices into projects for organized testing scenarios
- **Bulk Operations**: CSV import/export, bulk device creation, mass transmission control
- **Comprehensive Test Suite**: 59+ automated tests covering all components

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Frontend   │────▶│ API Service  │────▶│  PostgreSQL DB  │
│  (React)    │     │  (FastAPI)   │     │                 │
└──────┬──────┘     └──────────────┘     └─────────────────┘
       │                   │
       │  SSE              ▼
       │            ┌──────────────┐
       │            │ Transmission │
       │            │  Service     │
       │            │ (MQTT/HTTP/  │
       │            │  Kafka)      │
       │            └──────────────┘
       ▼
┌──────────────┐
│ Agent Service│ ◀── optional (--profile agent)
│ (AI Chat)    │
│ PydanticAI   │
└──────────────┘
```

### Services

- **API Service** (Port 8000): Main FastAPI backend for business logic
- **Transmission Service** (Port 8001): Dedicated service for IoT device transmissions
- **Agent Service** (Port 8002): AI assistant with SSE streaming chat *(optional, `--profile agent`)*
- **Frontend** (Port 5173): React/TypeScript SPA
- **PostgreSQL** (Port 5432): Primary database
- **Redis** (Port 6379): Caching and session management

## Deploy Notes

### Required Services (Core)

These services are mandatory for the application to function:

| Service | Purpose | Port | Required |
|---------|---------|------|----------|
| **PostgreSQL** | Primary database for all data | 5432 | ✅ Yes |
| **API Service** | Main FastAPI backend (business logic, auth, device management) | 8000 | ✅ Yes |
| **Transmission Service** | IoT device transmission handler (MQTT/HTTP/Kafka) | 8001 | ✅ Yes |
| **Redis** | Caching, sessions, and Celery broker | 6379 | ✅ Yes |
| **Frontend (Docker)** | A frontend served from Docker | ✅ Yes |

### Optional Services

| Service | When to Deploy | Profile |
|---------|----------------|---------|
| **Agent Service** | AI-powered assistant for natural language IoT management | `agent` |
| **MinIO** | When using `STORAGE_BACKEND=s3` for dataset storage | `storage` |
| **Celery Worker** | For background async tasks (large dataset generation, bulk operations) | `worker` |

### Deployment Options

#### Option 1: Full Docker Deployment (Recommended for Production)

Deploy all services:

```bash
# Clone and start all services
git clone <repository-url>
cd iot-devsim
cp .env.example .env
# Edit .env with your production settings

docker-compose up -d
```

#### Option 2: Hybrid - Backend in Docker, Frontend as External Service

Use this when you want to deploy the frontend separately (e.g., Vercel, Netlify, or custom CDN):

```bash
# Start only backend services (no frontend container)
docker-compose up -d postgres redis api-service transmission-service

# Or use profiles to exclude specific services
docker-compose up -d --scale frontend=0
```

Then deploy frontend externally:

```bash
cd frontend
npm install
npm run build
# Deploy 'dist/' folder to your static hosting
```

Configure frontend environment:
```bash
# .env.production or hosting environment variables
VITE_API_URL=https://your-api-domain.com
VITE_WS_URL=wss://your-api-domain.com/ws
```

#### Option 3: External S3/MinIO Storage

When using external MinIO or AWS S3 for datasets:

```bash
# Start core services + MinIO
docker-compose --profile storage up -d
```

Configure in `.env`:
```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://your-minio-domain.com/
S3_BUCKET=iot-devsim-datasets
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=us-east-1
```

#### Option 4: With AI Agent Assistant

Enable the conversational AI agent for natural language IoT management:

```bash
# Start core services + agent
docker compose --profile agent up -d
```

Configure in `.env`:
```env
LLM_PROVIDER=openai          # openai | anthropic | ollama
LLM_MODEL=gpt-4o-mini        # Model name for the provider
LLM_API_KEY=sk-proj-...      # API key (not needed for ollama)
VITE_AGENT_SERVICE_URL=http://localhost:8002/api/v1
```

See [`agent-service/README.md`](./agent-service/README.md) for full configuration.

#### Option 5: With Background Workers

For heavy async workloads:

```bash
# Start all services including Celery worker
docker-compose --profile worker up -d
```

### Storage Configuration

#### Local Storage (Default)
Uses Docker volumes for dataset storage:
```bash
# No additional configuration needed
# Datasets stored in: ./api-service/uploads/datasets
```

#### S3/MinIO Storage
For distributed or scalable storage:

1. **With Docker MinIO** (self-hosted):
   ```bash
   docker-compose --profile storage up -d minio
   ```

2. **With External MinIO/S3**:
   - Set `S3_ENDPOINT_URL` to your external endpoint
   - Do NOT start the MinIO profile

### Environment Variables

See `.env.example` for full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection URL (e.g., `redis://redis:6379/0`) |
| `REDIS_PORT` | ❌ | Redis port mapping for Docker (default: `6379`) |
| `JWT_SECRET_KEY` | ✅ | JWT signing secret (change in production!) |
| `STORAGE_BACKEND` | ❌ | `local` (default) or `s3` |
| `S3_ENDPOINT_URL` | ❌ | Required if `STORAGE_BACKEND=s3` |
| `S3_BUCKET` | ❌ | S3 bucket name |
| `S3_ACCESS_KEY` | ❌ | S3 access key |
| `S3_SECRET_KEY` | ❌ | S3 secret key |
| `TRANSMISSION_BATCH_SIZE` | ❌ | Messages per batch (default: 100) |
| `TRANSMISSION_INTERVAL_MS` | ❌ | Transmission interval (default: 1000) |
| `LLM_PROVIDER` | ❌ | AI agent LLM provider: `openai`, `anthropic`, `ollama` |
| `LLM_MODEL` | ❌ | LLM model name (e.g., `gpt-4o-mini`) |
| `LLM_API_KEY` | ❌ | API key for the LLM provider |
| `VITE_AGENT_SERVICE_URL` | ❌ | Frontend URL to agent service |

### Database Migrations

After deployment, run migrations:

```bash
# Inside Docker
docker-compose exec api-service alembic upgrade head

# Or manually
cd api-service
alembic upgrade head
```

### Production Checklist

- [ ] Change `JWT_SECRET_KEY` from default
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure proper `CORS_ORIGINS` for your domain
- [ ] Use strong database passwords
- [ ] Enable HTTPS for API endpoints
- [ ] Configure backup for PostgreSQL data
- [ ] Set up monitoring/alerting (optional)
- [ ] Use external S3/MinIO for large-scale storage (optional)

### Health Checks

All services expose health endpoints:
- API Service: `GET /health` (port 8000)
- Transmission Service: `GET /health` (port 8001)
- Agent Service: `GET /health` (port 8002) — includes LLM provider status at `/api/v1/health`

## Quick Start (Development)

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd iot-devsim

# Start core services
docker-compose up -d postgres redis

# Run backend services (manual for hot reload)
cd api-service
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal - Transmission Service
cd transmission-service
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# In another terminal - Frontend
cd frontend
npm install
npm run dev
```

## Testing

### Backend Tests (Transmission Service)

```bash
# Run tests inside Docker container
docker exec iot-devsim-transmission python -m pytest tests/ -v

# With coverage
docker exec iot-devsim-transmission python -m pytest tests/ --cov=app
```

### Frontend Tests

```bash
cd frontend
npm run test
npm run test:coverage
```

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `JWT_SECRET_KEY` | JWT signing secret | Change in production! |
| `TRANSMISSION_BATCH_SIZE` | Messages per batch | `100` |
| `TRANSMISSION_INTERVAL_MS` | Transmission interval | `1000` |

## Project Structure

```
iot-devsim-v2/
├── api-service/           # FastAPI backend
├── transmission-service/  # Transmission handling
├── agent-service/         # AI assistant (PydanticAI + SSE streaming)
├── frontend/             # React/TypeScript SPA
├── database/             # Database initialization
├── docs/                 # Project docs
├── docker-compose.yml    # Service orchestration
└── README.md             # This file
```

## Documentation

- [Product Overview](./docs/steering/product.md)
- [Technology Stack](./docs/steering/tech.md)
- [Project Structure](./docs/steering/structure.md)

## Contributing

1. Create a feature branch: `git checkout -b feature/name`
2. Make your changes with tests
3. Run the test suite: `docker exec iot-devsim-transmission python -m pytest tests/`
4. Commit with clear messages: `git commit -m "Add feature X"`
5. Push and create a Pull Request

### Code Standards

- **Python**: Type hints, PEP 8, async/await for I/O
- **TypeScript**: Strict mode, no `any` types, custom hooks
- **Testing**: All new features need tests

## Security

- JWT tokens for authentication (shared secret across services)
- Environment variables for secrets (never commit `.env`)
- Encrypted credentials for IoT connections
- Circuit breaker prevents cascading failures
- **AI Agent security** (defense-in-depth):
  - Anti prompt-injection with 22 regex patterns (3 threat levels)
  - Output filtering: redacts JWT tokens, API keys, PEM keys, passwords, emails
  - Action control: forbidden/confirmation-required classification
  - Per-user rate limiting (20 msg/min, 50 actions/session)
  - Audit logging with hashed message content (never stored raw)
  - Session isolation with TTL and LRU eviction

## License

MIT License - see LICENSE file for details.

---
