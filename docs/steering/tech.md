# Technology Stack and Build System

## Architecture Overview

IoT DevSim v2 follows a microservices architecture with the following components:

- **API Service**: FastAPI-based REST API for core business logic
- **Transmission Service**: Dedicated service for handling IoT device transmissions
- **Frontend**: React/TypeScript SPA with modern UI components
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache/Queue**: Redis for caching and background task management

## Backend Technology Stack

### Core Framework
- **FastAPI 0.104.1**: Modern Python web framework with automatic API documentation
- **Python 3.11**: Runtime environment
- **SQLAlchemy 2.0**: ORM with async support
- **Alembic**: Database migrations
- **Pydantic v2**: Data validation and serialization

### Database & Storage
- **PostgreSQL 17**: Primary database
- **Redis 8**: Caching and session management
- **AsyncPG**: Async PostgreSQL driver

### Security & Authentication
- **python-jose**: JWT token handling
- **passlib[bcrypt]**: Password hashing
- **cryptography**: Application-level encryption for sensitive data

### IoT Protocol Support
- **paho-mqtt**: MQTT client library (TCP, WebSocket, TLS support)
- **kafka-python**: Kafka producer (for Kafka protocol support)
- **httpx**: HTTP/HTTPS client with async support

### Testing Framework
- **pytest 7.4.3**: Python testing framework with async support
- **pytest-asyncio**: Async test execution
- **pytest-cov**: Code coverage reporting
- **factory-boy**: Test data factories
- **faker**: Fake data generation for tests

### Resilience Patterns
- **Connection Pooling**: Per-connection_id connection reuse with health checks
- **Circuit Breaker**: Failure detection with exponential backoff recovery
- **Retry Logic**: Exponential backoff on transient failures

### Monitoring & Logging
- **structlog**: Structured logging
- **prometheus-client**: Metrics collection
- **uvicorn**: ASGI server with auto-reload

## Frontend Technology Stack

### Core Framework
- **React 18.3**: UI library with hooks
- **TypeScript 5.6**: Type-safe JavaScript
- **Vite 5.4**: Build tool and dev server

### UI Components & Styling
- **Tailwind CSS 3.4**: Utility-first CSS framework
- **Radix UI**: Headless UI components
- **shadcn/ui**: Pre-built component library
- **Lucide React**: Icon library

### State Management & Data Fetching
- **Zustand 5.0**: Lightweight state management
- **TanStack Query 5.89**: Server state management
- **React Hook Form 7.62**: Form handling
- **Zod 4.1**: Schema validation

### Development Tools
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Vitest**: Unit testing framework
- **Playwright**: E2E testing

## Development Environment

### Containerization
- **Docker**: Container runtime
- **Docker Compose**: Multi-service orchestration
- Development and production Dockerfile stages

### Database Management
```bash
# Run migrations
cd api-service
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Common Development Commands

#### Backend (API Service)
```bash
# Start development server
cd api-service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Database operations
alembic upgrade head
alembic revision --autogenerate -m "migration_name"
```

#### Transmission Service (Tests)
```bash
# Run transmission service tests (inside Docker container)
docker exec iot-devsim-transmission python -m pytest tests/ -v

# Run with coverage
docker exec iot-devsim-transmission python -m pytest tests/ --cov=app --cov-report=term-missing
```

#### Frontend
```bash
# Start development server
cd frontend
npm run dev

# Install dependencies
npm install

# Build for production
npm run build

# Run tests
npm run test
npm run test:coverage

# Linting and formatting
npm run lint
npm run format
```

#### Full Stack (Docker)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api-service
docker-compose logs -f transmission-service

# Rebuild services
docker-compose build
docker-compose up -d --build

# Stop all services
docker-compose down
```

## Environment Configuration

### Required Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret for JWT token signing
- `CORS_ORIGINS`: Allowed frontend origins
- `ENVIRONMENT`: development/production

### Port Configuration
- API Service: 8000
- Transmission Service: 8001
- Frontend Dev Server: 5173
- PostgreSQL: 5432
- Redis: 6379

## Code Quality Standards

### Python (Backend)
- Use type hints for all function parameters and return values
- Follow PEP 8 style guidelines
- Use Pydantic models for data validation
- Implement proper error handling with structured logging
- Use async/await for I/O operations

### TypeScript (Frontend)
- Strict TypeScript configuration (no `any` types)
- Use proper component typing with React.FC or function components
- Implement proper error boundaries
- Use custom hooks for reusable logic
- Follow accessibility best practices (ARIA labels, semantic HTML)