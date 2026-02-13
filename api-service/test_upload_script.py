
import httpx
import asyncio
import os

API_URL = "http://127.0.0.1:8005/api/v1"
EMAIL = "test4@example.com"
PASSWORD = "Password123!"

async def test_upload():
    async with httpx.AsyncClient() as client:
        # 1. Login
        print(f"Logging in as {EMAIL}...")
        try:
            auth_response = await client.post(
                f"{API_URL}/auth/login",
                json={"email": EMAIL, "password": PASSWORD},  # Use json and 'email' field
                headers={"Content-Type": "application/json"}
            )
            auth_response.raise_for_status()
            token_data = auth_response.json()
            access_token = token_data["tokens"]["access_token"]
            print("Login successful.")
        except httpx.HTTPStatusError as e:
            print(f"Login failed: {e.response.text}")
            return
        
        # 2. Upload
        print("Uploading file...")
        file_path = r"c:\Users\joanlube\dev\iot\test_dataset.csv"
        files = {'file': ('test_dataset.csv', open(file_path, 'rb'), 'text/csv')}
        import time
        dataset_name = f"Test Script Dataset {int(time.time())}"
        data = {
            'name': dataset_name,
            'description': 'Test upload via script',
            'tags': '["test"]',
            'has_header': 'true',
            'delimiter': ',',
            'encoding': 'utf-8'
        }
        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        
        try:
            response = await client.post(
                f"{API_URL}/datasets/upload",
                files=files,
                data=data,
                headers=headers
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Upload request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload())
