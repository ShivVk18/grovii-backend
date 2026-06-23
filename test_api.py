import requests
import uuid

BASE_URL = "http://localhost:8000"
username = f"testuser_{uuid.uuid4().hex[:8]}"
email = f"{username}@example.com"
password = "testpassword123"

print(f"=== Testing API on {BASE_URL} ===")

# 1. Register User
print("\n--- 1. Register User ---")
res = requests.post(f"{BASE_URL}/auth/register", json={
    "username": username,
    "email": email,
    "password": password
})
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200

# 2. Login User
print("\n--- 2. Login User ---")
res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": email,
    "password": password
})
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Create Storyboard (POST)
print("\n--- 3. Create Storyboard ---")
payload = {
    "idea": "A cooking show for beginners",
    "goal": "Teach basic knife skills",
    "tone": "Educational",
    "style": "Fast-paced",
    "audience": "Young adults",
    "duration": 60,
    "platform": "YouTube"
}
res = requests.post(f"{BASE_URL}/storyboards", json=payload, headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 201
storyboard_id = res.json()["id"]

# 4. List Storyboards (GET)
print("\n--- 4. List Storyboards ---")
res = requests.get(f"{BASE_URL}/storyboards", headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200
assert len(res.json()) >= 1

# 5. Get Single Storyboard (GET)
print("\n--- 5. Get Single Storyboard ---")
res = requests.get(f"{BASE_URL}/storyboards/{storyboard_id}", headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200

# 6. Update Storyboard (PATCH)
print("\n--- 6. Update Storyboard ---")
res = requests.patch(f"{BASE_URL}/storyboards/{storyboard_id}", json={
    "title": "Mastering the Chef's Knife"
}, headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200
assert res.json()["title"] == "Mastering the Chef's Knife"

# 7. Delete Storyboard (DELETE)
print("\n--- 7. Delete Storyboard ---")
res = requests.delete(f"{BASE_URL}/storyboards/{storyboard_id}", headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200

# 8. Verify Deletion
print("\n--- 8. Verify Deletion ---")
res = requests.get(f"{BASE_URL}/storyboards/{storyboard_id}", headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 404

print("\n✅ All API tests passed successfully!")
