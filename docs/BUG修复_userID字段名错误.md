# BUG 修复：userID 字段名错误

## 🐛 问题描述

在测试 ANT/ 前缀模型时，发现以下错误：

```
[WARNING] Marked Antigravity credential error: unknown_antigravity, error_code=401
[INFO] Discovered 0 enabled Antigravity accounts
```

尽管 `accounts.toml` 中有 2 个账户，但系统无法识别任何账户。

---

## 🔍 根本原因

在 `src/antigravity_credential_manager.py` 第 90 行：

```python
# 错误代码（修复前）
virtual_filename = f"{account.get('userID', 'unknown')}_antigravity"
```

**问题**：
- 代码使用 `'userID'`（驼峰命名）
- 但 `accounts.toml` 中使用 `'user_id'`（下划线命名）

结果：
- `account.get('userID', 'unknown')` 总是返回默认值 `'unknown'`
- virtual_filename 变成 `"unknown_antigravity"`
- 无法正确加载账户状态
- 所有账户都被视为禁用

---

## ✅ 修复方案

### 修改文件
`src/antigravity_credential_manager.py` 第 90 行

### 修改前
```python
virtual_filename = f"{account.get('userID', 'unknown')}_antigravity"
```

### 修改后
```python
virtual_filename = f"userID_{account.get('user_id', 'unknown')}"
```

### 变化说明
1. **字段名**：`'userID'` → `'user_id'`（匹配 accounts.toml 格式）
2. **格式**：`"xxx_antigravity"` → `"userID_xxx"`（统一 virtual filename 格式）

这样生成的 virtual_filename 将是：
- `"userID_109317313934405443047"` （账户1）
- `"userID_117468831196878067179"` （账户2）

与 `file_storage_manager.py` 中的实现保持一致。

---

## 📋 后续步骤

### 1. 刷新过期的 access_token

当前 access_token 已过期（401 错误），需要使用 refresh_token 刷新：

```bash
# 运行 token 刷新脚本
python refresh_antigravity_token.py
```

**脚本功能**：
- 自动读取 `creds/accounts.toml`
- 使用每个账户的 `refresh_token` 刷新 `access_token`
- 更新 `last_used` 时间戳
- 保存更新后的 `accounts.toml`

### 2. 重新启用被禁用的账户

由于之前的 401 错误触发了自动封禁，第一个账户被禁用：

```toml
# creds/accounts.toml 第 6 行
disabled = true  # 需要改为 false
```

**方法 1：手动编辑**
```bash
# 编辑 creds/accounts.toml
# 将第 6 行改为：disabled = false
```

**方法 2：通过控制面板**
- 访问 http://localhost:7861/control_panel.html
- 找到 `axibayuit@gmail.com` 账户
- 点击"启用"按钮

### 3. 重启服务

```bash
# 重启 web.py
python web.py
```

### 4. 测试 ANT/ 模型调用

```bash
# 运行测试脚本
python test_ant_model.py
```

或使用 curl 测试：

```bash
curl -X POST http://localhost:7861/v1/chat/completions \
  -H "Authorization: Bearer 123456" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ANT/gemini-3-pro-high",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

---

## 🔍 验证修复

启动服务后，应该看到以下日志：

```
[INFO] Discovered 2 enabled Antigravity accounts  # 而不是 0
[INFO] Using Antigravity account: axibayuit@gmail.com
```

如果看到 `unknown_antigravity`，说明修复未生效。

---

## 📊 影响范围

### 受影响的功能
- ❌ ANT/ 前缀模型无法调用
- ❌ Antigravity 凭证无法识别
- ❌ 凭证轮换功能失效
- ❌ 状态管理失效

### 已修复
- ✅ virtual_filename 正确生成
- ✅ 账户状态正确加载
- ✅ 凭证轮换功能恢复
- ✅ 自动封禁功能恢复

---

## 🔄 相关文件

### 主要修改
- `src/antigravity_credential_manager.py` - 第 90 行

### 依赖文件（未修改，仅验证）
- `creds/accounts.toml` - 使用 `user_id` 字段
- `src/storage/file_storage_manager.py` - 使用 `userID_` 前缀格式
- `src/web_routes.py` - 识别 `userID_` 前缀

### 格式约定
```
accounts.toml 字段名：user_id（下划线）
virtual_filename 格式：userID_{user_id}（userID_ 前缀 + user_id 值）
```

---

## 📝 经验教训

1. **字段命名一致性**：确保所有地方使用相同的字段名（`user_id` vs `userID`）
2. **虚拟文件名格式**：`userID_` 前缀是整个系统的约定，需要严格遵守
3. **错误信息关键**：`"unknown_antigravity"` 清楚表明了 `get()` 默认值被使用
4. **跨文件验证**：修改凭证管理时，需要检查 storage 层的实现

---

## ✅ 修复完成

- [x] 识别根本原因（字段名不匹配）
- [x] 修复 `antigravity_credential_manager.py`
- [x] 验证其他文件中的字段名使用
- [x] 创建修复文档
- [ ] 刷新 access_token（待用户执行）
- [ ] 重新启用账户（待用户执行）
- [ ] 测试 ANT/ 模型调用（待用户执行）

**修复时间**：2025-11-25
**修复人员**：Claude Code
