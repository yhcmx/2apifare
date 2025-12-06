# Workers 代理与源码匹配分析

## 📋 检查时间
2025-12-06

## 🔍 检查项目

### 1. Python 源码请求路径分析

#### 1.1 Gemini CLI 请求
**源码位置**: `src/google_chat_api.py:230`
```python
target_url = f"{await get_code_assist_endpoint()}/v1internal:{action}"
# action = "streamGenerateContent" 或 "generateContent"
# 流式请求会添加: ?alt=sse
```

**默认配置**: `CODE_ASSIST_ENDPOINT=https://cloudcode-pa.googleapis.com`

**实际请求示例**:
- 流式: `POST https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse`
- 非流式: `POST https://cloudcode-pa.googleapis.com/v1internal:generateContent`

**请求头**:
```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "GeminiCLI/0.1.5 (Windows; AMD64)"  # 或其他系统
}
```

#### 1.2 Antigravity Token 刷新
**源码位置**: `src/antigravity_credential_manager.py:383-393`
```python
async with httpx.AsyncClient(timeout=30) as client:
    response = await client.post(
        "https://oauth2.googleapis.com/token",  # ⚠️ 硬编码，未使用配置
        headers={
            "Host": "oauth2.googleapis.com",
            "User-Agent": "Go-http-client/1.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip"
        },
        data=urlencode(data)
    )
```

**问题**:
- ❌ 直接硬编码 URL，**没有使用代理配置**
- ❌ httpx.AsyncClient 没有传递 proxy 参数
- ⚠️ 如果用户在受限网络环境，这个请求会失败

#### 1.3 Antigravity loadCodeAssist
**源码位置**: `src/antigravity_credential_manager.py:845-848`
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        'https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:loadCodeAssist',
        headers={...}
    )
```

**问题**: 同样硬编码，未使用代理

---

### 2. Workers 代理路由配置

**源码位置**: `docs/geminicli .txt`

```javascript
const routeMap = {
  '/oauth2': 'oauth2.googleapis.com',
  '/crm': 'cloudresourcemanager.googleapis.com',
  '/usage': 'serviceusage.googleapis.com',
  '/api': 'www.googleapis.com',
  '/code': 'cloudcode-pa.googleapis.com'
};
```

**路径转换逻辑**:
```javascript
url.hostname = targetHost;
url.pathname = path.replace(matchedPrefix, '');
```

---

### 3. 路径匹配测试

#### 测试用例 1: Gemini CLI 请求
**用户配置**: `CODE_ASSIST_ENDPOINT=https://gcli2api.workers.dev/code`

**请求流程**:
1. Python 发送: `POST https://gcli2api.workers.dev/code/v1internal:streamGenerateContent?alt=sse`
2. Workers 接收路径: `/code/v1internal:streamGenerateContent`
3. 匹配前缀: `/code` ✅
4. 目标主机: `cloudcode-pa.googleapis.com`
5. 路径替换: `/code/v1internal:streamGenerateContent`.replace(`/code`, ``) = `/v1internal:streamGenerateContent`
6. 最终请求: `https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse` ✅

**结论**: ✅ **完全匹配**

#### 测试用例 2: Antigravity Token 刷新
**硬编码 URL**: `https://oauth2.googleapis.com/token`

**问题分析**:
- Python 直接请求 `https://oauth2.googleapis.com/token`
- **不会经过 Workers 代理**
- 在国内或受限网络环境下会失败

**解决方案**:
需要修改 Python 源码，使用可配置的代理端点：
```python
oauth_endpoint = await get_antigravity_oauth_endpoint()  # 已有此配置
# 如果用户配置为: https://gcli2api.workers.dev/oauth2/token
```

---

### 4. 请求头匹配检查

#### 4.1 Python 发送的请求头
```python
# Gemini CLI
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "GeminiCLI/0.1.5 (Windows; AMD64)"
}

# Antigravity Token 刷新
headers = {
    "Host": "oauth2.googleapis.com",  # ⚠️ 显式设置了 Host
    "User-Agent": "Go-http-client/1.1",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Encoding": "gzip"
}
```

#### 4.2 Workers 处理请求头
```javascript
const newHeaders = new Headers(request.headers);

// ✅ 修复1：设置正确的 Host 头
newHeaders.set('Host', targetHost);

// 删除 Cloudflare 特有的头
newHeaders.delete('cf-connecting-ip');
newHeaders.delete('cf-ipcountry');
newHeaders.delete('cf-ray');
newHeaders.delete('cf-visitor');
newHeaders.delete('x-forwarded-proto');
newHeaders.delete('x-real-ip');
```

**分析**:
- ✅ Workers 会重新设置 `Host` 为目标主机（如 `oauth2.googleapis.com`）
- ✅ 保留了 `Authorization`, `Content-Type`, `User-Agent` 等关键头
- ✅ 删除了 Cloudflare 特征头，避免被识别

---

### 5. 请求方法和 Body 匹配

#### 5.1 Python 请求
```python
# POST 请求，带 JSON body
resp = await client.stream(
    "POST", target_url,
    content=final_post_data,  # JSON 字符串
    headers=headers
)
```

#### 5.2 Workers 处理
```javascript
body: request.method !== 'GET' && request.method !== 'HEAD'
  ? request.body
  : undefined,
```

**分析**:
- ✅ POST 请求正确传递 body
- ✅ GET/HEAD 请求不传递 body（符合 HTTP 规范）

---

## 🐛 发现的问题

### 问题 1: Antigravity 凭证刷新未使用代理
**严重程度**: ⚠️ 中等

**影响**:
- 在国内或受限网络环境下，Antigravity token 刷新会失败
- 用户必须能直连 `oauth2.googleapis.com`

**建议修复**:
修改 `src/antigravity_credential_manager.py:383-393`，使用配置的代理端点。

### 问题 2: Antigravity loadCodeAssist 未使用代理
**严重程度**: ⚠️ 中等

**影响**: 同问题 1

**建议修复**:
使用配置的 Antigravity API 端点。

### 问题 3: httpx.AsyncClient 未使用全局代理配置
**严重程度**: ⚠️ 中等

**当前代码**:
```python
async with httpx.AsyncClient(timeout=30) as client:
```

**应该使用**:
```python
from src.httpx_client import http_client

async with http_client.get_client(timeout=30) as client:
```

这样可以自动使用 `config.py` 中的 `PROXY` 配置。

---

## ✅ 验证通过的部分

1. ✅ Workers 路由映射与 Python 配置端点对应
2. ✅ 路径替换逻辑正确（`/code/v1internal:xxx` → `/v1internal:xxx`）
3. ✅ Host 头正确设置（已修复）
4. ✅ GET/HEAD 请求不带 body（已修复）
5. ✅ CORS 头正确注入
6. ✅ 关键请求头（Authorization, Content-Type）正确传递

---

## 🎯 cloudcode-pa.googleapis.com 高错误率原因分析

根据代码检查，可能的原因：

1. ❌ **之前的 Bug（已修复）**:
   - `Host` 头被删除 → 导致 Google API 拒绝请求（4xx）
   - GET 请求带 body → 可能导致某些 API 报错

2. ✅ **修复后应该解决**:
   - 设置正确的 `Host: cloudcode-pa.googleapis.com`
   - GET 请求不再带 body

3. ⚠️ **其他可能原因**:
   - Token 过期/无效（应该由 Python 端处理）
   - 请求参数错误（Python 端问题）
   - Google API 限流（需要检查 429 错误）

---

## 📝 总结

### 当前 Workers 代理代码状态
✅ **已修复主要问题，可以部署使用**

### 需要后续改进的地方
1. Python 源码中 Antigravity 相关请求应使用可配置的代理端点
2. 统一使用 `http_client` 模块的全局代理配置

### 建议监控指标
- `cloudcode-pa.googleapis.com` 的 4xx/5xx 错误率
- `oauth2.googleapis.com` 的成功率
- 请求延迟

---

**报告生成时间**: 2025-12-06
**检查者**: Claude Code Analysis
