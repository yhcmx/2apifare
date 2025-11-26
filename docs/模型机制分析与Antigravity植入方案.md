# 模型机制分析与 Antigravity 植入方案

## 📊 一、CLI 源码模型机制详解

### 1.1 模型生成架构

#### 核心配置
```python
# 基础模型列表
BASE_MODELS = [
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    # ... 共9个基础模型
]

# 公共API模型（不支持功能前缀）
PUBLIC_API_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]
```

#### 模型变体生成规则

每个基础模型会生成 **13个变体**（PUBLIC_API_MODELS 除外）：

```
基础模型（1个）
├─ gemini-2.5-flash

功能前缀变体（2个）
├─ 假流式/gemini-2.5-flash
└─ 流式抗截断/gemini-2.5-flash

Thinking 后缀变体（3个）
├─ gemini-2.5-flash-maxthinking
├─ gemini-2.5-flash-nothinking
└─ gemini-2.5-flash-search

功能前缀 + Thinking 后缀组合（6个）
├─ 假流式/gemini-2.5-flash-maxthinking
├─ 假流式/gemini-2.5-flash-nothinking
├─ 假流式/gemini-2.5-flash-search
├─ 流式抗截断/gemini-2.5-flash-maxthinking
├─ 流式抗截断/gemini-2.5-flash-nothinking
└─ 流式抗截断/gemini-2.5-flash-search
```

#### 模型总数计算
```
GeminiCLI模型总数 = 7个普通模型 × 13个变体 + 2个PUBLIC_API模型 × 1个变体
                 = 91 + 2 = 93个模型
```

---

## 🎭 二、功能前缀/后缀详解

### 2.1 假流式（`假流式/` 前缀）

#### 原理

```python
# 1. 检测到假流式模型，将 stream=True 改为 False
if use_fake_streaming and request_data.stream:
    request_data.stream = False
    return await fake_stream_response(api_payload, cred_mgr)

# 2. 先获取完整的非流式响应
async def fake_stream_response():
    # 发送心跳保持连接
    heartbeat = {"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}]}
    yield heartbeat

    # 每3秒发送心跳，直到收到完整响应
    while not response_task.done():
        await asyncio.sleep(3.0)
        yield heartbeat

    # 3. 获取完整响应
    response = await response_task

    # 4. 逐字模拟流式发送
    for char in content:
        yield streaming_chunk(char)
        await asyncio.sleep(0.01)  # 模拟打字效果
```

#### 适用场景

| 场景 | 说明 |
|------|------|
| 客户端兼容性差 | 客户端对真实流式支持不好，假流式更稳定 |
| 需要完整响应 | 等待完整响应后再逐字展示，避免中途断开 |
| 打字机效果 | 用户喜欢逐字显示效果，但需要保证内容完整 |
| 调试和日志 | 方便记录完整响应用于调试 |

#### 区别对比

| 对比项 | 真流式 | 假流式 |
|--------|--------|--------|
| 响应速度 | 快（边生成边发送） | 慢（等待完整响应） |
| 稳定性 | 较差（可能中途断开） | 高（完整响应后发送） |
| 首字延迟 | 低（立即开始） | 高（等待完整响应） |
| 内存占用 | 低（流式传输） | 高（缓存完整响应） |
| 适用场景 | 实时对话 | 长文本生成 |

---

### 2.2 流式抗截断（`流式抗截断/` 前缀）

#### 原理

```python
# 1. 在 systemInstruction 中添加 [done] 标记指令
system_instruction = {
    "parts": [{
        "text": """严格执行以下输出结束规则：
1. 当你完成完整回答时，必须在输出的最后单独一行输出：[done]
2. [done] 标记表示你的回答已经完全结束
3. 只有输出了 [done] 标记，系统才认为你的回答是完整的
...
"""
    }]
}

# 2. 监听流式响应
async for chunk in stream:
    # 检测是否包含 [done] 标记
    if "[done]" in chunk_text:
        log.info("检测到 [done] 标记，响应完整")
        break

    # 检测是否被截断（MAX_TOKENS）
    if finish_reason == "MAX_TOKENS":
        log.warn(f"检测到截断（第{attempt}次），准备续写...")

        # 3. 添加续写消息
        payload["request"]["contents"].append({
            "role": "user",
            "parts": [{
                "text": """请从刚才被截断的地方继续输出剩余的所有内容。

重要提醒：
1. 不要重复前面已经输出的内容
2. 直接继续输出，无需任何前言或解释
3. 当你完整完成所有内容输出后，必须在最后一行单独输出：[done]
4. [done] 标记表示你的回答已经完全结束，这是必需的结束标记

现在请继续输出："""
            }]
        })

        # 4. 发送续写请求（最多3次）
        async for continuation_chunk in send_gemini_request(payload):
            yield continuation_chunk
```

#### 配置参数

```python
# 最大续写次数（默认3次）
anti_truncation_max_attempts = 3

# 完成标记
DONE_MARKER = "[done]"

# 续写提示模板
CONTINUATION_PROMPT = """请从刚才被截断的地方继续输出剩余的所有内容。

重要提醒：
1. 不要重复前面已经输出的内容
2. 直接继续输出，无需任何前言或解释
3. 当你完整完成所有内容输出后，必须在最后一行单独输出：[done]
...
"""
```

#### 工作流程

```
第1次请求（原始请求）
  ↓
发送请求 → 检测 finish_reason
  ↓
finish_reason == "MAX_TOKENS"?
  ├─ 否 → 检测 [done] 标记？
  │     ├─ 是 → 完成，停止输出
  │     └─ 否 → 继续输出下一个chunk
  └─ 是 → 第2次请求（续写）
        ↓
      添加续写提示 → 发送请求
        ↓
      finish_reason == "MAX_TOKENS"?
        ├─ 否 → 检测 [done] 标记？完成
        └─ 是 → 第3次请求（续写）
              ↓
            ... 最多重试 anti_truncation_max_attempts 次
```

#### 适用场景

| 场景 | 说明 |
|------|------|
| 长文本生成 | 技术文档、长篇文章、详细分析报告 |
| 代码生成 | 完整的代码文件、多个函数实现 |
| 教程生成 | 分步骤教程、详细说明文档 |
| 避免截断 | 需要完整输出而不是分段请求 |

#### 区别对比

| 对比项 | 不抗截断 | 抗截断 |
|--------|----------|--------|
| 遇到截断 | 直接停止 | 自动续写 |
| 完整性 | 可能不完整 | 保证完整 |
| 请求次数 | 1次 | 1-N次（N≤3） |
| API调用成本 | 低 | 高（多次调用） |
| 适用场景 | 短对话 | 长文本生成 |

---

### 2.3 Thinking 后缀

#### `-maxthinking`（最大思考预算）

```python
thinking_budget = 32768  # tokens

# 适用场景：
# - 复杂推理任务
# - 数学证明
# - 深度代码分析
# - 需要详细思考过程
```

#### `-nothinking`（限制思考）

```python
thinking_budget = 128  # tokens

# 适用场景：
# - 简单问答
# - 快速响应
# - 降低成本
# - 不需要详细思考过程
```

#### `-search`（搜索增强）

```python
# 启用 Google Search Grounding
search_grounding = True

# 适用场景：
# - 需要最新信息
# - 实时数据查询
# - 新闻事件
# - 结合搜索结果回答
```

---

## 🚀 三、Antigravity 模型植入方案

### 3.1 设计原则

#### ✅ 核心设计理念

1. **独立分类**
   - 使用 `ANT/` 前缀标识 Antigravity 模型
   - 与 GeminiCLI 模型明确区分
   - 便于路由和处理逻辑分离

2. **不添加功能前缀**
   - Antigravity API 本身已经是流式的（不需要"假流式/"）
   - Antigravity API 有自己的续写机制（不需要"流式抗截断/"）
   - 避免功能冲突和混淆

3. **保持原始模型名**
   - 不添加额外的 thinking 后缀
   - 保留 API 返回的原始模型名称
   - 简化配置和维护

4. **统一的模型列表**
   - GeminiCLI 和 Antigravity 模型统一在 `/v1/models` 端点返回
   - 客户端可以通过前缀区分模型来源
   - 简化客户端集成

---

### 3.2 实现方案

#### 配置文件修改（`config.py`）

```python
# ============================================================================
# Antigravity Models Configuration (Gemini 3.0)
# ============================================================================

# Antigravity 基础模型列表（从 Google Antigravity API 获取）
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

# 已经包含特殊后缀的 Antigravity 模型（不再添加功能后缀）
ANTIGRAVITY_SPECIAL_MODELS = [
    "claude-sonnet-4-5-thinking",
    "gemini-2.5-flash-thinking",
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
]


def get_antigravity_models():
    """
    获取 Antigravity 模型列表

    设计原则：
    1. Antigravity API 本身已经是流式的，不需要"假流式"前缀
    2. Antigravity API 有自己的续写机制，不需要"流式抗截断"前缀
    3. 使用 ANT/ 前缀标识，便于区分来源和路由
    4. 保持原始模型名称，不添加额外的功能后缀

    Returns:
        List[str]: Antigravity 模型名称列表
    """
    models = []

    for base_model in ANTIGRAVITY_BASE_MODELS:
        # 添加基础模型（带 ANT/ 前缀标识）
        models.append(f"ANT/{base_model}")

    return models


def is_antigravity_model(model_name: str) -> bool:
    """检查是否是 Antigravity 模型"""
    return model_name.startswith("ANT/")


def get_antigravity_base_model(model_name: str) -> str:
    """从 ANT/ 前缀模型名获取基础模型名"""
    if model_name.startswith("ANT/"):
        return model_name[4:]  # 移除 "ANT/" 前缀
    return model_name


def get_available_models(router_type="openai"):
    """
    获取所有可用模型列表

    包含：
    1. GeminiCLI 模型（带功能前缀）
    2. Antigravity 模型（ANT/ 前缀）

    Returns:
        List[str]: 所有模型名称列表
    """
    models = []

    # 1. GeminiCLI 模型（带功能前缀）
    for base_model in BASE_MODELS:
        # ... 生成变体 ...

    # 2. Antigravity 模型（ANT/ 前缀）
    models.extend(get_antigravity_models())

    return models
```

---

### 3.3 测试结果

```
============================================================
模型列表统计
============================================================
GeminiCLI 模型数量: 86
Antigravity 模型数量: 13
总模型数量: 99

Antigravity 基础模型: 13个

============================================================
Antigravity 模型列表 (共 13 个)
============================================================
 1. ANT/chat_23310                    -> chat_23310
 2. ANT/chat_20706                    -> chat_20706
 3. ANT/claude-sonnet-4-5             -> claude-sonnet-4-5
 4. ANT/claude-sonnet-4-5-thinking    -> claude-sonnet-4-5-thinking
 5. ANT/gemini-2.5-flash-lite         -> gemini-2.5-flash-lite
 6. ANT/gemini-2.5-flash-image        -> gemini-2.5-flash-image
 7. ANT/gemini-2.5-flash              -> gemini-2.5-flash
 8. ANT/gemini-2.5-flash-thinking     -> gemini-2.5-flash-thinking
 9. ANT/gemini-2.5-pro                -> gemini-2.5-pro
10. ANT/gemini-3-pro-high             -> gemini-3-pro-high
11. ANT/gemini-3-pro-image            -> gemini-3-pro-image
12. ANT/gemini-3-pro-low              -> gemini-3-pro-low
13. ANT/gpt-oss-120b-medium           -> gpt-oss-120b-medium
```

---

## 📌 四、Antigravity 与 GeminiCLI 对比

### 4.1 模型数量对比

| 类型 | 基础模型数 | 变体数 | 总模型数 |
|------|-----------|--------|----------|
| GeminiCLI | 9 | 每个模型13个变体 | 93 |
| Antigravity | 13 | 每个模型1个变体 | 13 |
| **总计** | **22** | - | **106** |

### 4.2 功能对比

| 功能 | GeminiCLI | Antigravity |
|------|-----------|-------------|
| 假流式 | ✅ 支持（假流式/ 前缀） | ❌ 不需要（API本身流式） |
| 抗截断 | ✅ 支持（流式抗截断/ 前缀） | ❌ 不需要（API自动续写） |
| Thinking模式 | ✅ 支持（-maxthinking/-nothinking/-search） | ⚠️ 部分模型自带（如 -thinking 后缀） |
| 搜索增强 | ✅ 支持（-search 后缀） | ❓ 未知（待确认） |
| 流式传输 | ✅ 支持 | ✅ 原生支持 |
| 凭证管理 | ✅ 支持（creds/xxx.json） | ✅ 支持（creds/userID_xxx） |

### 4.3 API 端点对比

| 对比项 | GeminiCLI | Antigravity |
|--------|-----------|-------------|
| 聊天端点 | `https://cloudcode-pa.googleapis.com` | `https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse` |
| 模型列表端点 | - | `https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:fetchAvailableModels` |
| OAuth端点 | `https://oauth2.googleapis.com` | `https://oauth2.googleapis.com/token` |
| 认证方式 | OAuth2 (CLI) | OAuth2 (Web) |
| 凭证格式 | JSON (project_id, access_token) | TOML (email, access_token, refresh_token) |

---

## 🎯 五、使用示例

### 5.1 GeminiCLI 模型使用

```bash
# 基础模型
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'

# 假流式模型
curl ... -d '{
  "model": "假流式/gemini-2.5-flash",
  ...
}'

# 抗截断模型
curl ... -d '{
  "model": "流式抗截断/gemini-2.5-flash",
  ...
}'

# 最大思考模型
curl ... -d '{
  "model": "gemini-2.5-flash-maxthinking",
  ...
}'

# 组合使用
curl ... -d '{
  "model": "假流式/gemini-2.5-flash-maxthinking",
  ...
}'
```

### 5.2 Antigravity 模型使用

```bash
# Antigravity 模型（ANT/ 前缀）
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ANT/gemini-3-pro-high",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'

# Claude 模型
curl ... -d '{
  "model": "ANT/claude-sonnet-4-5",
  ...
}'

# Thinking 模型（自带 -thinking 后缀）
curl ... -d '{
  "model": "ANT/claude-sonnet-4-5-thinking",
  ...
}'

# Gemini 3.0 高性能模型
curl ... -d '{
  "model": "ANT/gemini-3-pro-high",
  ...
}'
```

---

## 📊 六、总结

### 6.1 核心优势

✅ **独立分类**：ANT/ 前缀清晰区分模型来源
✅ **简化配置**：不添加不必要的功能前缀
✅ **统一接口**：所有模型通过 `/v1/models` 统一返回
✅ **灵活扩展**：方便后续添加新的 Antigravity 模型
✅ **向后兼容**：不影响现有 GeminiCLI 模型的使用

### 6.2 植入完成清单

- [x] 添加 `ANTIGRAVITY_BASE_MODELS` 配置
- [x] 实现 `get_antigravity_models()` 函数
- [x] 实现 `is_antigravity_model()` 检测函数
- [x] 实现 `get_antigravity_base_model()` 解析函数
- [x] 修改 `get_available_models()` 集成两类模型
- [x] 修改 `get_base_model_from_feature_model()` 支持 ANT/ 前缀
- [x] 测试模型列表生成（99个模型）

### 6.3 下一步工作

- [ ] 修改 `openai_router.py` 添加 Antigravity 模型路由
- [ ] 修改 `gemini_router.py` 添加 Antigravity 模型路由
- [ ] 实现 Antigravity 凭证轮换机制
- [ ] 测试 Antigravity 模型的实际调用
- [ ] 添加 Antigravity 模型的错误处理
- [ ] 更新控制面板显示 Antigravity 模型状态
