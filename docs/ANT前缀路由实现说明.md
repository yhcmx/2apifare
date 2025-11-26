# ANT/ 前缀路由实现说明

## 📋 实现概述

已成功实现 `ANT/` 前缀模型的自动路由到 Antigravity API，当用户使用 `ANT/` 开头的模型名时，系统会：

1. **自动识别**：检测模型名的 `ANT/` 前缀
2. **使用 Antigravity 凭证**：从 `accounts.toml` 获取 Antigravity 凭证
3. **调用 Antigravity API**：使用 Antigravity 适配器处理请求
4. **自动轮换**：支持凭证自动轮换和错误处理

---

## 🗂️ 文件结构

### 新增文件

```
src/
├── antigravity_credential_manager.py  # Antigravity 凭证管理器（新增）
├── openai_router.py                   # 添加了 ANT/ 路由逻辑（修改）
└── storage/
    └── file_storage_manager.py        # 添加了 load_antigravity_accounts（修改）

antigravity/
├── __init__.py                        # 适配器模块
├── client.py                          # API 客户端
├── converter.py                       # 格式转换器
└── auth.py                            # OAuth 认证

config.py                              # 添加了 Antigravity 模型列表（修改）
```

---

## 🔄 工作流程

### 1. 模型检测

```python
# openai_router.py: 133-141

model = request_data.model

# 检测是否是 Antigravity 模型（ANT/ 前缀）
if is_antigravity_model(model):
    log.info(f"Detected Antigravity model: {model}")
    return await handle_antigravity_request(request_data)

# 否则继续 GeminiCLI 逻辑
```

### 2. 凭证获取

```python
# openai_router.py: 499-515

# 获取 Antigravity 凭证管理器
ant_cred_mgr = await get_antigravity_credential_manager()

# 获取有效凭证（自动轮换）
credential_result = await ant_cred_mgr.get_valid_credential()

account = credential_result["account"]
virtual_filename = credential_result["virtual_filename"]
access_token = account.get("access_token")

log.info(f"Using Antigravity account: {account.get('email', 'unknown')}")
```

### 3. 请求转换

```python
# openai_router.py: 521-567

# 提取 system_instruction
system_instruction = "你是一个有帮助的 AI 助手。"
for msg in request_data.messages:
    if msg.role == "system":
        system_instruction += msg.content

# 转换消息格式（OpenAI → Antigravity）
openai_messages = [
    {"role": msg.role, "content": msg.content}
    for msg in user_messages
]

# 生成 Antigravity 请求体
antigravity_payload = generate_request_body(
    openai_messages=openai_messages,
    model_name=base_model,  # 移除 ANT/ 前缀
    parameters={"temperature": 1.0, "max_tokens": 200},
    openai_tools=request_data.tools,
    system_instruction=system_instruction
)
```

### 4. API 调用

```python
# openai_router.py: 577-624

# 流式响应
async for chunk in stream_generate_content(antigravity_payload, access_token, proxy):
    # 转换为 OpenAI 格式
    openai_chunk = convert_sse_to_openai_format(chunk, base_model, stream_id, created)
    yield openai_chunk.encode()

# 发送结束块
finish_chunk = generate_finish_chunk(base_model, has_tool_calls, stream_id, created)
yield finish_chunk.encode()

# 标记成功
await ant_cred_mgr.mark_credential_success(virtual_filename)
```

### 5. 错误处理

```python
# openai_router.py: 599-622

except Exception as e:
    log.error(f"Antigravity streaming error: {e}")

    # 检查 HTTP 错误码
    if "403 Forbidden" in error_message:
        await ant_cred_mgr.mark_credential_error(virtual_filename, 403)
    elif "401" in error_message:
        await ant_cred_mgr.mark_credential_error(virtual_filename, 401)

    # 发送错误块给客户端
    error_chunk = { ... }
    yield f"data: {json.dumps(error_chunk)}\n\n".encode()
```

---

## 📊 Antigravity 凭证管理器

### 核心功能

```python
# src/antigravity_credential_manager.py

class AntigravityCredentialManager:
    """Antigravity 凭证管理器"""

    async def initialize(self):
        """初始化：加载 accounts.toml"""

    async def _discover_credentials(self):
        """从 accounts.toml 加载凭证"""

    async def get_valid_credential(self):
        """获取有效凭证（自动轮换）"""

    async def mark_credential_error(self, virtual_filename, error_code):
        """标记凭证错误"""

    async def disable_credential(self, virtual_filename):
        """禁用凭证"""

    async def mark_credential_success(self, virtual_filename):
        """标记凭证成功"""
```

### 凭证轮换

```python
# 调用次数达到 calls_per_rotation 时自动轮换
if self._call_count >= calls_per_rotation:
    await self._rotate_credential()

# 重置计数，移到下一个账号
self._current_credential_index = (self._current_credential_index + 1) % len(self._credential_accounts)
self._call_count = 0
```

### 自动封禁

```python
# 检查是否需要自动封禁
auto_ban_enabled = await get_auto_ban_enabled()
auto_ban_error_codes = await get_auto_ban_error_codes()  # [401, 403, 404]

if auto_ban_enabled and error_code in auto_ban_error_codes:
    await self.disable_credential(virtual_filename)
```

---

## 🔧 配置说明

### 模型列表配置

```python
# config.py

# Antigravity 基础模型（13个）
ANTIGRAVITY_BASE_MODELS = [
    "chat_23310",
    "chat_20706",
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-thinking",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-image",
    "gemini-2.5-flash",
    "gemini-2.5-flash-thinking",
    "gemini-2.5-pro",
    "gemini-3-pro-high",
    "gemini-3-pro-image",
    "gemini-3-pro-low",
    "gpt-oss-120b-medium",
]

# 生成 ANT/ 前缀模型
def get_antigravity_models():
    return [f"ANT/{model}" for model in ANTIGRAVITY_BASE_MODELS]
```

### 端点配置

```toml
# creds/config.toml

# Antigravity API 端点
antigravity_api_endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

# Antigravity 模型列表端点
antigravity_models_endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:fetchAvailableModels"

# Antigravity OAuth 端点
antigravity_oauth_endpoint = "https://oauth2.googleapis.com/token"
```

### 凭证配置

```toml
# creds/accounts.toml

[[accounts]]
userID = "123456789"
email = "example@gmail.com"
access_token = "ya29.a0..."
refresh_token = "1//..."
last_used = "2025-11-25 22:00:00"
```

---

## 🧪 测试方法

### 1. 使用测试脚本

```bash
# 运行测试脚本
python test_ant_model.py

# 测试 3 个模型：
# - ANT/gemini-3-pro-high
# - ANT/claude-sonnet-4-5
# - ANT/gemini-2.5-flash
```

### 2. 使用 curl

```bash
# 测试 Antigravity 模型
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ANT/gemini-3-pro-high",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true,
    "temperature": 1.0,
    "max_tokens": 200
  }'
```

### 3. 查看日志

```bash
# 查看日志输出
tail -f logs/gcli2api.log

# 关键日志：
# [INFO] Detected Antigravity model: ANT/gemini-3-pro-high
# [INFO] Using Antigravity account: example@gmail.com
# [INFO] Antigravity credential manager initialized with 2 accounts
```

---

## 📌 功能对比

| 功能 | GeminiCLI 模型 | Antigravity 模型 (ANT/) |
|------|---------------|------------------------|
| **前缀** | 无 / `假流式/` / `流式抗截断/` | `ANT/` |
| **凭证来源** | `creds/*.json` | `creds/accounts.toml` |
| **API 端点** | `cloudcode-pa.googleapis.com` | `daily-cloudcode-pa.sandbox.googleapis.com` |
| **凭证格式** | JSON (project_id, access_token) | TOML (email, access_token, refresh_token) |
| **假流式** | ✅ 支持 | ❌ 不需要（API本身流式） |
| **抗截断** | ✅ 支持 | ❌ 不需要（API自动续写） |
| **凭证轮换** | ✅ 支持 | ✅ 支持 |
| **自动封禁** | ✅ 支持 | ✅ 支持 |
| **模型数量** | 93个（带变体） | 13个（无变体） |
| **状态管理** | `creds.toml` | `accounts.toml` + `creds.toml` |

---

## 🎯 使用示例

### OpenAI SDK (Python)

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:7861/v1",
    api_key="YOUR_API_PASSWORD"
)

# 使用 Antigravity 模型
response = client.chat.completions.create(
    model="ANT/gemini-3-pro-high",
    messages=[
        {"role": "user", "content": "你好，请介绍你自己。"}
    ],
    stream=True,
    temperature=1.0,
    max_tokens=200
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### OpenAI SDK (Node.js)

```javascript
const OpenAI = require('openai');

const client = new OpenAI({
  baseURL: 'http://localhost:7861/v1',
  apiKey: 'YOUR_API_PASSWORD'
});

// 使用 Antigravity 模型
const response = await client.chat.completions.create({
  model: 'ANT/claude-sonnet-4-5',
  messages: [
    { role: 'user', content: 'Hello, introduce yourself.' }
  ],
  stream: true,
  temperature: 1.0,
  max_tokens: 200
});

for await (const chunk of response) {
  if (chunk.choices[0]?.delta?.content) {
    process.stdout.write(chunk.choices[0].delta.content);
  }
}
```

### curl

```bash
# Gemini 3.0 高性能模型
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ANT/gemini-3-pro-high",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'

# Claude Sonnet 4.5
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ANT/claude-sonnet-4-5",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

---

## 🚀 下一步优化

### 1. Token 自动刷新

```python
# TODO: 检测 401 错误时自动刷新 access_token
if "401" in error_message:
    # 使用 refresh_token 刷新
    new_token = await refresh_antigravity_token(refresh_token)
    # 更新 accounts.toml
    # 重试请求
```

### 2. 非流式响应支持

```python
# TODO: 实现非流式响应
if not is_streaming:
    # 缓存完整响应
    # 返回 JSONResponse
```

### 3. gemini_router.py 支持

```python
# TODO: 在 gemini_router.py 中添加 ANT/ 路由
# 支持 Gemini 格式的 API 调用
```

### 4. 控制面板显示

```python
# TODO: 在控制面板显示 Antigravity 账号状态
# 支持通过 Web 界面管理 accounts.toml
```

---

## ✅ 完成清单

- [x] 创建 Antigravity 凭证管理器
- [x] 实现 ANT/ 模型检测
- [x] 添加 Antigravity 路由逻辑
- [x] 集成 Antigravity 适配器
- [x] 实现凭证自动轮换
- [x] 实现错误处理和自动封禁
- [x] 支持流式响应
- [x] 创建测试脚本
- [ ] 实现 Token 自动刷新
- [ ] 支持非流式响应
- [ ] 添加 gemini_router.py 支持
- [ ] 更新控制面板

---

## 📝 总结

**ANT/ 前缀路由已成功实现！**

现在当你使用 `ANT/` 开头的模型名（如 `ANT/gemini-3-pro-high`）时：

1. ✅ 系统自动识别并路由到 Antigravity API
2. ✅ 从 `accounts.toml` 获取 Antigravity 凭证
3. ✅ 支持凭证自动轮换
4. ✅ 支持错误处理和自动封禁
5. ✅ 完全兼容 OpenAI SDK

只需要：
- 在 `creds/accounts.toml` 中配置你的 Antigravity 账号
- 使用 `ANT/` 前缀调用模型
- 享受 Gemini 3.0 和 Claude 4.5 的强大能力！🎉
