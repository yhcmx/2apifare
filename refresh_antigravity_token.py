"""
刷新 Antigravity access token
"""
import asyncio
import os
import toml
import httpx
import time

# OAuth 配置（来自 antigravity/auth.py）
CLIENT_ID = '1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com'
CLIENT_SECRET = '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'


async def refresh_token(refresh_token_value: str) -> dict:
    """
    刷新 access token

    Args:
        refresh_token_value: refresh_token

    Returns:
        {'access_token': str, 'expires_in': int}
    """
    # 动态获取 OAuth 端点配置
    from config import get_antigravity_oauth_endpoint

    token_url = await get_antigravity_oauth_endpoint()

    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token_value
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed ({response.status_code}): {response.text}")


async def main():
    """刷新 accounts.toml 中的所有 token"""
    accounts_file = "creds/accounts.toml"

    if not os.path.exists(accounts_file):
        print(f"Error: File not found: {accounts_file}")
        return

    print("Loading accounts.toml...")
    with open(accounts_file, 'r', encoding='utf-8') as f:
        accounts_data = toml.load(f)

    if not accounts_data.get('accounts'):
        print("Error: No accounts found")
        return

    print(f"Found {len(accounts_data['accounts'])} account(s)")

    for i, account in enumerate(accounts_data['accounts']):
        email = account.get('email', f'Account {i+1}')
        refresh_token_value = account.get('refresh_token')

        if not refresh_token_value:
            print(f"\n[{i+1}] {email}: SKIP (no refresh_token)")
            continue

        print(f"\n[{i+1}] {email}")
        print(f"  Refreshing token...")

        try:
            token_data = await refresh_token(refresh_token_value)

            # 更新 access_token
            account['access_token'] = token_data['access_token']

            # 更新时间戳
            account['last_used'] = time.strftime('%Y-%m-%d %H:%M:%S')

            print(f"  Success!")
            print(f"  New access_token: {token_data['access_token'][:50]}...")
            print(f"  Expires in: {token_data['expires_in']} seconds ({token_data['expires_in']//60} minutes)")

        except Exception as e:
            print(f"  Failed: {e}")
            continue

    # 保存更新后的文件
    print(f"\nSaving to {accounts_file}...")
    with open(accounts_file, 'w', encoding='utf-8') as f:
        toml.dump(accounts_data, f)

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
