"""Update dataset status to ready so it can be linked to devices."""
import requests

BASE = "http://localhost:8000/api/v1"

t = requests.post(f"{BASE}/auth/login", json={
    "email": "test@iot-devsim.com",
    "password": "Test1234!"
}).json()["tokens"]["access_token"]
h = {"Authorization": f"Bearer {t}"}

ds = requests.get(f"{BASE}/datasets?skip=0&limit=5", headers=h).json()["items"]
d = [x for x in ds if x["name"] == "Temperature Readings"][0]
print(f"Dataset: {d['id']} Status: {d['status']}")

r = requests.patch(f"{BASE}/datasets/{d['id']}", json={"status": "ready"}, headers=h)
print(f"Patch: {r.status_code} {r.text[:300]}")
