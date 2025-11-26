import requests
import json
import time

# 读取Antigravity凭证
with open(r"D:\Research\fandai\2apifare\docs\antigravity2api-nodejs\data\accounts.json", 'r') as f:
    accounts = json.load(f)

account = accounts[0]
refresh_token = account['refresh_token']

print("=" * 70)
print("Step 1: Refreshing Antigravity Access Token")
print("=" * 70)

# 使用Antigravity的Client ID刷新token
CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
CLIENT_SECRET = "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"

refresh_data = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token
}

try:
    response = requests.post(
        'https://oauth2.googleapis.com/token',
        data=refresh_data,
        timeout=10
    )

    if response.status_code == 200:
        token_data = response.json()
        new_access_token = token_data['access_token']
        print(f"[OK] Token refreshed successfully")
        print(f"New access_token (first 20 chars): {new_access_token[:20]}...")
        print(f"Expires in: {token_data.get('expires_in', 'N/A')} seconds")

        # 更新accounts.json
        account['access_token'] = new_access_token
        account['expires_in'] = token_data.get('expires_in', 3599)
        account['timestamp'] = int(time.time() * 1000)

        with open(r"D:\Research\fandai\2apifare\docs\antigravity2api-nodejs\data\accounts.json", 'w') as f:
            json.dump(accounts, f, indent=2)
        print("[OK] Updated accounts.json")

    else:
        print(f"[ERROR] Refresh failed: {response.status_code}")
        print(f"Response: {response.text}")
        exit(1)

except Exception as e:
    print(f"[ERROR] Refresh request failed: {e}")
    exit(1)

print("\n" + "=" * 70)
print("Step 2: Testing with Gemini CLI API")
print("=" * 70)

# 测试Gemini CLI API
url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {'Authorization': f'Bearer {new_access_token}'}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"\n[SUCCESS] Got {len(models)} models from Gemini CLI API")
        print("\nFirst 5 models:")
        for model in models[:5]:
            print(f"  - {model.get('name', 'N/A')}")

        print("\n" + "=" * 70)
        print("CONCLUSION: Antigravity credential WORKS with Gemini CLI API!")
        print("=" * 70)
        print("\nThis means:")
        print("- We only need ONE credential system (Antigravity)")
        print("- One credential can access BOTH APIs")
        print("- Gemini 2.5, 3.0, and Claude - all with one credential!")

    elif response.status_code == 403:
        print(f"\n[ERROR] 403 Forbidden")
        print(f"Response: {response.text}")
        print("\nConclusion: Antigravity credential cannot access Gemini CLI API")

    else:
        print(f"\n[ERROR] Unexpected status: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"\n[ERROR] Request failed: {e}")

print("\n" + "=" * 70)
print("Step 3: Testing content generation")
print("=" * 70)

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
headers = {
    'Authorization': f'Bearer {new_access_token}',
    'Content-Type': 'application/json'
}
data = {
    "contents": [{
        "parts": [{"text": "Say 'Hello' in one word"}]
    }]
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        print(f"\n[SUCCESS] Generation worked!")
        print(f"Response: {text.strip()}")
        print("\n" + "=" * 70)
        print("FINAL CONFIRMATION: Antigravity credential is FULLY COMPATIBLE!")
        print("=" * 70)
    else:
        print(f"\n[ERROR] Generation failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"\n[ERROR] Generation request failed: {e}")
