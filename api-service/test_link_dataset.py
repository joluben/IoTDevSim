"""Test linking a dataset to a device via the API."""
import requests

BASE = "http://localhost:8000/api/v1"

r = requests.post(f"{BASE}/auth/login", json={
    "email": "test@iot-devsim.com",
    "password": "Test1234!"
})
token = r.json()["tokens"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get device
devs = requests.get(f"{BASE}/devices?skip=0&limit=5", headers=headers).json()["items"]
device = [d for d in devs if d["name"] == "Temperature Sensor A1"][0]
print(f"Device: {device['id']} ({device['name']})")

# Get dataset
datasets = requests.get(f"{BASE}/datasets?skip=0&limit=5", headers=headers).json()["items"]
ds = [d for d in datasets if d["name"] == "Temperature Readings"][0]
print(f"Dataset: {ds['id']} ({ds['name']})")

# Link dataset to device
r4 = requests.post(
    f"{BASE}/devices/{device['id']}/datasets",
    json={"dataset_id": ds["id"]},
    headers=headers
)
print(f"Link status: {r4.status_code}")
print(f"Link body: {r4.text[:500]}")
