"""Create test data for Playwright E2E tests: an MQTT connection and a dataset."""
import requests

BASE = "http://localhost:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={
    "email": "test@iot-devsim.com",
    "password": "Test1234!"
})
token = r.json()["tokens"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create MQTT connection
conn_resp = requests.post(f"{BASE}/connections", json={
    "name": "Test MQTT Broker",
    "protocol": "mqtt",
    "is_active": True,
    "config": {
        "broker_url": "mqtt://localhost",
        "port": 1883,
        "topic": "iot/test/data",
        "client_id": "test-client",
        "qos": 1
    }
}, headers=headers)
print("Connection:", conn_resp.status_code, conn_resp.text[:300])

# Create dataset
ds_resp = requests.post(f"{BASE}/datasets", json={
    "name": "Temperature Readings",
    "description": "Sample temperature data for testing",
    "source": "generated",
    "tags": ["temperature", "test"],
    "columns": [
        {"name": "temperature", "data_type": "float", "position": 0, "description": "Temperature in Celsius"},
        {"name": "humidity", "data_type": "float", "position": 1, "description": "Humidity percentage"},
        {"name": "timestamp", "data_type": "string", "position": 2, "description": "ISO timestamp"}
    ]
}, headers=headers)
print("Dataset:", ds_resp.status_code, ds_resp.text[:300])
