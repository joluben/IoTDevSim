# IoT DevSim v2 - Product Overview

## Product Description

IoT DevSim v2 is a comprehensive IoT device simulation and management platform designed for testing and development of IoT systems. The platform enables developers to simulate thousands of IoT devices, manage their connections, and monitor data transmission in real-time.

## Core Features

- **Connection Management**: Support for multiple IoT protocols (MQTT, HTTP/HTTPS, Kafka) with secure credential storage and connection testing
- **Device Simulation**: Create and manage virtual IoT devices with customizable data payloads and transmission patterns
- **Project Organization**: Group devices into projects for organized testing scenarios and bulk operations
- **Real-time Monitoring**: Live dashboard with transmission logs, performance metrics, and system health monitoring
- **Bulk Operations**: CSV import/export, bulk device creation, and mass transmission control
- **Connection Pooling**: Efficient connection reuse per device connection to minimize connection overhead
- **Circuit Breaker Pattern**: Automatic failure detection with graceful degradation and exponential backoff recovery
- **Resilient Error Handling**: Retry logic with exponential backoff, detailed error logging to TransmissionLog.metadata, and automatic device status updates on persistent failures
- **Health Monitoring**: Periodic connection health checks with automatic invalidation of unhealthy connections
- **Comprehensive Test Suite**: 59+ automated tests covering protocol handlers, connection pooling, circuit breaker, and transmission manager integration

## Target Users

- IoT developers testing device connectivity and data flows
- QA engineers validating IoT system performance under load
- DevOps teams monitoring IoT infrastructure and protocols
- System architects designing scalable IoT solutions

## Key Value Propositions

- Simulate up to 5,000 concurrent device transmissions
- Test multiple IoT protocols in a unified platform
- Reduce physical hardware requirements for IoT testing
- Comprehensive monitoring and analytics for performance optimization