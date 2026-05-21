import httpx

base_url = "http://localhost:8000"

# Step 1 - Login
login = httpx.post(
    f"{base_url}/api/agent/login",
    json={
        "email": "posting-agent@ledgerflow.com",  # AGENT_EMAIL
        "password":"local-agent-password"    # AGENT_PASSWORD
    }
)
print(login.status_code)
print(login.json())
token = login.json()["access_token"]
print("✅ Logged in successfully")

# Step 2 - Upload xlsx file
headers = {"Authorization": f"Bearer {token}"}

file_path = r"C:\Users\acer\Downloads\financial_sample_dataset.xlsx"

with open(file_path, "rb") as f:
    response = httpx.post(
        f"{base_url}/api/agent/upload",
        headers=headers,
        files={"file": ("financial_sample_dataset.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=120.0
    )

print("Status:", response.status_code)
print("Response:", response.json())