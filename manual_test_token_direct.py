"""
直接测试 Antigravity token 是否有效
"""
import asyncio
import toml
import httpx
import json


async def test_token(access_token: str, email: str):
    """测试单个 token"""
    print(f"\n{'='*60}")
    print(f"测试账户: {email}")
    print(f"Token 前缀: {access_token[:50]}...")
    print('='*60)

    # API 配置（从 Node.js 版本复制）
    api_url = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"
    api_host = "daily-cloudcode-pa.sandbox.googleapis.com"
    user_agent = "antigravity/1.11.3 windows/amd64"

    # 请求头（完全按照 Node.js 版本）
    headers = {
        'Host': api_host,
        'User-Agent': user_agent,
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip'
    }

    # 简单的测试请求体
    request_body = {
        "model_id": "gemini-3-pro-high",
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "parameters": {
            "temperature": 1.0,
            "max_tokens": 50
        },
        "system_instruction": "你是一个有帮助的AI助手。"
    }

    try:
        print("\n发送测试请求...")
        print(f"URL: {api_url}")
        print(f"Headers: {json.dumps({k: v if k != 'Authorization' else f'Bearer {access_token[:20]}...' for k, v in headers.items()}, indent=2)}")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(api_url, json=request_body, headers=headers)

            print(f"\n响应状态码: {response.status_code}")

            if response.status_code == 200:
                print("✅ Token 有效！")
                # 读取前几行响应
                content = response.text[:500]
                print(f"\n响应前 500 字符:\n{content}")
                return True
            else:
                print(f"❌ Token 无效或有错误")
                error_text = response.text
                print(f"\n错误响应:\n{error_text}")
                return False

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("Antigravity Token 直接测试")
    print("="*60)

    # 读取 accounts.toml
    with open('creds/accounts.toml', 'r', encoding='utf-8') as f:
        accounts_data = toml.load(f)

    accounts = accounts_data.get('accounts', [])
    print(f"\n找到 {len(accounts)} 个账户")

    results = []
    for i, account in enumerate(accounts):
        email = account.get('email', f'Account {i+1}')
        access_token = account.get('access_token')
        disabled = account.get('disabled', False)

        if disabled:
            print(f"\n[{i+1}] {email}: SKIP (已禁用)")
            continue

        if not access_token:
            print(f"\n[{i+1}] {email}: SKIP (无 access_token)")
            continue

        result = await test_token(access_token, email)
        results.append((email, result))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = 0
    for email, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {email}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 个 token 有效")


if __name__ == "__main__":
    asyncio.run(main())
