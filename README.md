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
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Transmission │
                    │  Service     │
                    │ (MQTT/HTTP/  │
                    │  Kafka)      │
                    └──────────────┘
```

### Services

- **API Service** (Port 8000): Main FastAPI backend for business logic
- **Transmission Service** (Port 8001): Dedicated service for IoT device transmissions
- **Frontend** (Port 5173): React/Type SPA
- **PostgreSQL** (Port 5432): Primary database
- **Redis** (Port 6379): Caching and session management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd iot-devsim-v2

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Setup

#### 1. Database Setup
```bash
# PostgreSQL must be running
# Update .env with your database credentials
cp .env.example .env
```

#### 2. API Service
```bash
cd api-service
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Transmission Service
```bash
cd transmission-service
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

#### 4. Frontend
```bash
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
├── frontend/             # React/TypeScript SPA
├── database/             # Database initialization
├── documentation/        # Project docs
├── docker-compose.yml    # Service orchestration
└── README.md            # This file
```

## Documentation

- [Product Overview](./documentation/steering/product.md)
- [Technology Stack](./documentation/steering/tech.md)
- [Project Structure](./documentation/steering/structure.md)
- [Implementation Plan](./documentation/transmission-service-implementation-fix.md)

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

- JWT tokens for authentication
- Environment variables for secrets (never commit `.env`)
- Encrypted credentials for IoT connections
- Circuit breaker prevents cascading failures

## License

MIT License - see LICENSE file for details.

---

**Status**: Phases 1-6 complete. Connection pooling, circuit breaker, and comprehensive test suite operational.
