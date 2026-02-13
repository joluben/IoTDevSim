"""
Database Seed Data Script
Creates initial data for development and testing
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List
import uuid
import secrets
import string

# Add the api-service to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api-service'))

from app.core.database import AsyncSessionLocal, engine, Base
from app.models import User, Project, Device, Connection, TransmissionLog
from app.models.device import DeviceType, DeviceStatus
from app.models.connection import ConnectionType, ConnectionStatus
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_secure_password(length=16):
    """Generate a cryptographically secure random password for seed data."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# Generate or load seed passwords from environment
SEED_ADMIN_PASSWORD = os.getenv('SEED_ADMIN_PASSWORD', generate_secure_password())
SEED_DEMO_PASSWORD = os.getenv('SEED_DEMO_PASSWORD', generate_secure_password())


async def create_seed_data():
    """Create seed data for development"""
    print("Creating seed data...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Create admin user
            admin_user = User(
                email="admin@iot-devsim.com",
                full_name="System Administrator",
                hashed_password=pwd_context.hash(SEED_ADMIN_PASSWORD),
                is_active=True,
                is_verified=True,
                is_superuser=True,
                roles=["admin", "user"],
                permissions=["*"],
                preferences={
                    "theme": "dark",
                    "notifications": True,
                    "dashboard_layout": "grid"
                }
            )
            session.add(admin_user)
            await session.flush()
            
            # Create demo user
            demo_user = User(
                email="demo@iot-devsim.com",
                full_name="Demo User",
                hashed_password=pwd_context.hash(SEED_DEMO_PASSWORD),
                is_active=True,
                is_verified=True,
                is_superuser=False,
                roles=["user"],
                permissions=["devices:read", "devices:write", "projects:read", "projects:write"],
                preferences={
                    "theme": "light",
                    "notifications": True,
                    "dashboard_layout": "list"
                }
            )
            session.add(demo_user)
            await session.flush()
            
            # Create sample projects
            smart_home_project = Project(
                name="Smart Home Demo",
                description="Demonstration of smart home IoT devices and automation",
                is_active=True,
                is_public=True,
                owner_id=admin_user.id,
                settings={
                    "auto_simulation": True,
                    "data_retention_days": 90,
                    "alert_thresholds": {
                        "temperature": {"min": 15, "max": 30},
                        "humidity": {"min": 30, "max": 70}
                    }
                },
                max_devices=100,
                max_connections=50
            )
            session.add(smart_home_project)
            
            industrial_project = Project(
                name="Industrial Monitoring",
                description="Industrial equipment monitoring and predictive maintenance",
                is_active=True,
                is_public=False,
                owner_id=demo_user.id,
                settings={
                    "auto_simulation": False,
                    "data_retention_days": 365,
                    "maintenance_schedule": "weekly"
                },
                max_devices=500,
                max_connections=200
            )
            session.add(industrial_project)
            await session.flush()
            
            # Create sample devices for Smart Home project
            devices = []
            
            # Temperature sensors
            for i in range(3):
                device = Device(
                    name=f"Temperature Sensor {i+1}",
                    device_id=f"TEMP-{str(uuid.uuid4())[:8].upper()}",
                    description=f"Smart temperature sensor for room {i+1}",
                    device_type=DeviceType.SENSOR,
                    manufacturer="SensorTech",
                    model="ST-TEMP-2024",
                    firmware_version="1.2.3",
                    status=DeviceStatus.ONLINE,
                    is_active=True,
                    project_id=smart_home_project.id,
                    capabilities=["temperature", "humidity", "battery_level"],
                    metadata={
                        "location": f"Room {i+1}",
                        "installation_date": "2024-01-15",
                        "calibration_date": "2024-01-20"
                    },
                    configuration={
                        "sampling_rate": 60,  # seconds
                        "precision": 0.1,
                        "units": "celsius"
                    },
                    simulation_enabled=True,
                    simulation_config={
                        "temperature_range": [18, 25],
                        "humidity_range": [40, 60],
                        "variation": 0.5
                    }
                )
                devices.append(device)
                session.add(device)
            
            # Smart switches
            for i in range(2):
                device = Device(
                    name=f"Smart Switch {i+1}",
                    device_id=f"SW-{str(uuid.uuid4())[:8].upper()}",
                    description=f"Smart light switch for zone {i+1}",
                    device_type=DeviceType.ACTUATOR,
                    manufacturer="SmartHome Inc",
                    model="SH-SW-PRO",
                    firmware_version="2.1.0",
                    status=DeviceStatus.ONLINE,
                    is_active=True,
                    project_id=smart_home_project.id,
                    capabilities=["on_off", "dimming", "scheduling"],
                    metadata={
                        "location": f"Zone {i+1}",
                        "max_load": "1000W",
                        "installation_date": "2024-01-10"
                    },
                    configuration={
                        "default_brightness": 80,
                        "fade_time": 2,
                        "schedule_enabled": True
                    },
                    simulation_enabled=True,
                    simulation_config={
                        "state_changes_per_hour": 5,
                        "random_dimming": True
                    }
                )
                devices.append(device)
                session.add(device)
            
            # Gateway device
            gateway = Device(
                name="Home Gateway",
                device_id=f"GW-{str(uuid.uuid4())[:8].upper()}",
                description="Central gateway for smart home network",
                device_type=DeviceType.GATEWAY,
                manufacturer="NetworkPro",
                model="NP-GW-5000",
                firmware_version="3.0.1",
                status=DeviceStatus.ONLINE,
                is_active=True,
                project_id=smart_home_project.id,
                capabilities=["routing", "protocol_translation", "data_aggregation"],
                metadata={
                    "location": "Network Closet",
                    "ip_address": "192.168.1.1",
                    "supported_protocols": ["MQTT", "HTTP", "CoAP"]
                },
                configuration={
                    "mqtt_broker": "localhost:1883",
                    "data_retention": 24,  # hours
                    "backup_enabled": True
                },
                simulation_enabled=False
            )
            devices.append(gateway)
            session.add(gateway)
            await session.flush()
            
            # Create connections between devices
            connections = []
            
            # Connect sensors to gateway
            for i, sensor in enumerate([d for d in devices if d.device_type == DeviceType.SENSOR]):
                connection = Connection(
                    name=f"Sensor {i+1} to Gateway",
                    description=f"MQTT connection from {sensor.name} to gateway",
                    connection_type=ConnectionType.MQTT,
                    status=ConnectionStatus.ACTIVE,
                    is_active=True,
                    source_device_id=sensor.id,
                    target_device_id=gateway.id,
                    project_id=smart_home_project.id,
                    configuration={
                        "topic": f"sensors/temperature/{sensor.device_id}",
                        "qos": 1,
                        "retain": True,
                        "keepalive": 60
                    },
                    qos_level=1,
                    retain_messages=True,
                    simulation_enabled=True,
                    simulation_config={
                        "message_interval": 60,  # seconds
                        "message_size_range": [50, 200]  # bytes
                    }
                )
                connections.append(connection)
                session.add(connection)
            
            # Connect switches to gateway
            for i, switch in enumerate([d for d in devices if d.device_type == DeviceType.ACTUATOR]):
                connection = Connection(
                    name=f"Gateway to Switch {i+1}",
                    description=f"Control connection from gateway to {switch.name}",
                    connection_type=ConnectionType.MQTT,
                    status=ConnectionStatus.ACTIVE,
                    is_active=True,
                    source_device_id=gateway.id,
                    target_device_id=switch.id,
                    project_id=smart_home_project.id,
                    configuration={
                        "topic": f"actuators/switch/{switch.device_id}/command",
                        "qos": 2,
                        "retain": False,
                        "keepalive": 60
                    },
                    qos_level=2,
                    retain_messages=False,
                    simulation_enabled=True,
                    simulation_config={
                        "command_interval": 300,  # seconds
                        "command_types": ["on", "off", "dim"]
                    }
                )
                connections.append(connection)
                session.add(connection)
            
            await session.flush()
            
            # Create sample transmission logs
            print("Creating sample transmission logs...")
            
            # Generate logs for the past 24 hours
            now = datetime.utcnow()
            start_time = now - timedelta(hours=24)
            
            log_entries = []
            for connection in connections:
                # Generate logs every 5 minutes for the past 24 hours
                current_time = start_time
                while current_time < now:
                    # Sensor data transmission
                    if connection.source_device.device_type == DeviceType.SENSOR:
                        log = TransmissionLog(
                            device_id=connection.source_device_id,
                            connection_id=connection.id,
                            timestamp=current_time,
                            message_type="sensor_data",
                            direction="sent",
                            payload_size=120,
                            protocol="mqtt",
                            topic=connection.get_config("topic"),
                            qos_level=connection.qos_level,
                            status="success",
                            latency_ms=15,
                            is_simulated=True,
                            metadata={
                                "temperature": round(20 + (current_time.hour % 24) * 0.5, 1),
                                "humidity": round(45 + (current_time.minute % 60) * 0.3, 1)
                            }
                        )
                        log_entries.append(log)
                    
                    current_time += timedelta(minutes=5)
            
            # Batch insert logs
            session.add_all(log_entries)
            
            await session.commit()
            print(f"✅ Seed data created successfully!")
            print(f"   - Users: 2 (admin@iot-devsim.com, demo@iot-devsim.com)")
            print(f"   - Projects: 2")
            print(f"   - Devices: {len(devices)}")
            print(f"   - Connections: {len(connections)}")
            print(f"   - Transmission Logs: {len(log_entries)}")
            print(f"   - Admin password: {SEED_ADMIN_PASSWORD}")
            print(f"   - Demo password: {SEED_DEMO_PASSWORD}")
            print(f"   ⚠️  NOTE: These are auto-generated secure passwords for development only.")
            print(f"      Set SEED_ADMIN_PASSWORD and SEED_DEMO_PASSWORD env vars for reproducible seeds.")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating seed data: {e}")
            raise


async def main():
    """Main function to run seed data creation"""
    print("IoT DevSim v2 - Database Seed Data Creation")
    print("=" * 50)
    
    try:
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create seed data
        await create_seed_data()
        
    except Exception as e:
        print(f"❌ Failed to create seed data: {e}")
        return 1
    
    finally:
        await engine.dispose()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
