# Project Structure and Organization

## Repository Overview

The IoT DevSim v2 project follows a monorepo structure with clear separation of concerns across multiple services and components.

```
iot-devsim-v2/
├── api-service/           # Main FastAPI backend service
├── transmission-service/  # Dedicated transmission handling service
├── frontend/             # React/TypeScript frontend application
├── database/             # Database initialization and seed data
├── documentation/        # Project documentation and diagrams
├── example/              # Example/demo implementation
├── docker-compose.yml    # Multi-service orchestration
└── .env.example         # Environment configuration template
```

## Backend Services Structure

### API Service (`api-service/`)

```
api-service/
├── app/
│   ├── api/v1/           # API endpoints organized by version
│   │   ├── endpoints/    # Individual endpoint modules
│   │   │   ├── auth.py
│   │   │   ├── connections.py
│   │   │   ├── devices.py
│   │   │   ├── projects.py
│   │   │   └── users.py
│   │   └── router.py     # Main API router
│   ├── core/             # Core application configuration
│   │   ├── config.py     # Application settings
│   │   ├── database.py   # Database connection and session
│   │   ├── security.py   # Authentication and security utilities
│   │   └── encryption.py # Data encryption utilities
│   ├── middleware/       # Custom middleware components
│   │   ├── logging.py    # Request/response logging
│   │   └── security.py   # Security headers and rate limiting
│   ├── models/           # SQLAlchemy database models
│   │   ├── base.py       # Base model class
│   │   ├── user.py       # User model
│   │   ├── connection.py # Connection model
│   │   ├── device.py     # Device model
│   │   └── project.py    # Project model
│   ├── repositories/     # Data access layer
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic layer
│   │   ├── protocols/    # Protocol-specific handlers
│   │   │   ├── mqtt_handler.py
│   │   │   ├── http_handler.py
│   │   │   └── kafka_handler.py
│   │   └── connection_testing.py
│   └── main.py          # FastAPI application entry point
├── alembic/             # Database migrations
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
└── Dockerfile          # Container configuration
```

### Transmission Service (`transmission-service/`)

```
transmission-service/
├── app/
│   ├── api/v1/          # Transmission-specific API endpoints
│   │   └── endpoints/
│   │       └── transmission.py
│   ├── core/            # Core configuration (shared patterns with api-service)
│   │   ├── config.py    # Transmission service settings
│   │   ├── database.py  # Async SQLAlchemy session
│   │   └── logging.py   # Structured logging (structlog)
│   ├── models.py        # Standalone models (Device, Connection, TransmissionLog)
│   └── services/        # Transmission management logic
│       ├── transmission_manager.py    # Core transmission orchestration
│       ├── connection_pool.py       # Connection pooling per connection_id
│       ├── circuit_breaker.py       # Circuit breaker with exponential backoff
│       └── protocols/               # Protocol handlers with pooling support
│           ├── __init__.py          # Protocol registry
│           ├── base.py              # ProtocolHandler base class
│           ├── mqtt_handler.py        # MQTT/WebSocket MQTT (TCP/TLS/ws/wss)
│           ├── http_handler.py        # HTTP/HTTPS webhooks
│           └── kafka_handler.py     # Kafka producer
├── tests/               # Comprehensive test suite (59+ tests)
│   ├── __init__.py
│   ├── conftest.py      # pytest fixtures
│   ├── test_circuit_breaker.py
│   ├── test_connection_pool.py
│   ├── test_protocol_handlers.py
│   └── test_transmission_manager.py
├── pytest.ini         # pytest configuration
├── requirements.txt   # Service-specific dependencies
├── requirements-dev.txt # Development dependencies (pytest, etc.)
└── Dockerfile         # Container configuration
```

## Frontend Structure (`frontend/`)

### Application Architecture

```
frontend/src/
├── app/                 # Application-level configuration
│   ├── config/          # Constants, environment, navigation
│   ├── providers/       # React context providers (theme, query)
│   ├── router/          # React Router configuration
│   └── store/           # Zustand state management
├── components/          # Reusable UI components
│   ├── ui/              # shadcn/ui base components
│   ├── common/          # Shared application components
│   ├── layout/          # Layout components (header, sidebar, etc.)
│   ├── auth/            # Authentication-related components
│   ├── connections/     # Connection management components
│   └── forms/           # Form components and utilities
├── features/            # Feature-based organization
│   ├── auth/            # Authentication feature
│   ├── connections/     # Connection management feature
│   ├── dashboard/       # Dashboard feature
│   └── profile/         # User profile feature
├── hooks/               # Custom React hooks
├── pages/               # Page-level components
├── services/            # API communication layer
├── types/               # TypeScript type definitions
├── utils/               # Utility functions and helpers
├── styles/              # Global styles and Tailwind configuration
└── tests/               # Test files organized by feature
```

### Component Organization Principles

- **UI Components** (`components/ui/`): Base shadcn/ui components, no business logic
- **Common Components** (`components/common/`): Shared components with minimal business logic
- **Feature Components** (`components/{feature}/`): Feature-specific components
- **Page Components** (`pages/`): Top-level route components that compose features

## Database Structure (`database/`)

```
database/
├── init/                # Database initialization scripts
│   └── 01-init-database.sql
└── seed_data.py        # Development seed data
```

## Configuration and Environment

### Environment Files
- `.env.example`: Template for environment variables
- `api-service/.env`: API service specific configuration
- `frontend/.env`: Frontend specific configuration

### Docker Configuration
- `docker-compose.yml`: Multi-service orchestration with:
  - PostgreSQL database
  - Redis cache
  - API service
  - Transmission service
  - Network configuration and health checks

## Development Workflow Structure

### Code Organization Rules

1. **Separation of Concerns**: Each service has its own dependencies and configuration
2. **Shared Models**: Database models are shared between API and transmission services
3. **API Versioning**: All API endpoints are versioned (`/api/v1/`)
4. **Feature-Based Frontend**: Frontend organized by features, not technical layers
5. **Type Safety**: Comprehensive TypeScript usage with strict configuration

### File Naming Conventions

- **Python**: Snake_case for files and modules
- **TypeScript**: kebab-case for files, PascalCase for components
- **Database**: Snake_case for tables and columns
- **API Endpoints**: kebab-case for URLs

### Import Organization

#### Python Services
```python
# Standard library imports
# Third-party imports
# Local application imports (app.*)
```

#### Frontend
```typescript
// React and external libraries
// Internal utilities and types
// Component imports
// Relative imports
```

## Testing Structure

### Backend Testing
- Unit tests alongside source files
- Integration tests in dedicated test directories
- Property-based testing for critical business logic

### Frontend Testing
```
frontend/src/tests/
├── components/         # Component unit tests
├── features/          # Feature integration tests
├── pages/             # Page-level tests
├── services/          # API service tests
├── e2e/               # End-to-end tests
└── mocks/             # Test mocks and fixtures
```

## Documentation Structure

```
documentation/
├── database.sqlite.graphml      # Database schema diagram
├── frontend_implementation_plan.md
└── iot_devsim_implementation_plan.md
```

This structure supports:
- Clear separation between services
- Scalable feature development
- Maintainable code organization
- Efficient development workflows
- Comprehensive testing strategies