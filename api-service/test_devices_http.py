"""Test the devices endpoint via HTTP to see the actual error."""
import requests

# Login first
login_resp = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "test@iot-devsim.com",
    "password": "Test1234!"
})
print("Login status:", login_resp.status_code)
token = login_resp.json()["tokens"]["access_token"]

# List devices
resp = requests.get("http://localhost:8000/api/v1/devices", 
    params={"skip": 0, "limit": 10},
    headers={"Authorization": f"Bearer {token}"}
)
print("Devices status:", resp.status_code)
print("Devices body:", resp.text[:500])

# Try creating a device
create_resp = requests.post("http://localhost:8000/api/v1/devices", 
    json={"name": "Test Sensor", "device_type": "sensor"},
    headers={"Authorization": f"Bearer {token}"}
)
print("Create status:", create_resp.status_code)
print("Create body:", create_resp.text[:500])
