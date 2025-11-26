# Antigravity Credentials Format 说明

## 文件位置
`creds/accounts.toml`

## 数据结构

增强版的 Antigravity 凭证现在包含以下丰富的信息：

### 凭证字段说明

```toml
[[accounts]]
# ============ Token 信息 ============
access_token = "ya29.a0AfB_..."           # Google OAuth 访问令牌
refresh_token = "1//0gXXXXXX..."         # 刷新令牌（用于自动续期）
expires_in = 3599                         # Token 过期时间（秒）
token_type = "Bearer"                     # Token 类型
scope = "https://www.googleapis.com/..."  # 授权范围

# ============ 时间戳信息 ============
timestamp = 1732531200000                 # Unix 时间戳（毫秒）
created_at = "2025-11-25 18:00:00"       # 创建时间（可读格式）
last_used = "2025-11-25 18:00:00"        # 最后使用时间

# ============ 启用状态 ============
enable = true                             # 是否启用此凭证

# ============ 用户信息 ============
email = "user@gmail.com"                  # 📧 用户邮箱
name = "张三"                             # 👤 用户名称
picture = "https://lh3.googleusercontent.com/a/..."  # 头像 URL
verified_email = true                     # ✔️ 邮箱是否已验证
user_id = "123456789012345678901"        # Google 用户唯一 ID
locale = "zh-CN"                          # 语言环境

# ============ 项目信息 ============
project_count = 3                         # 📁 关联的项目总数

[[accounts.projects]]                     # 项目列表（最多10个）
project_id = "my-project-123"            # 项目 ID
project_name = "My First Project"        # 项目名称
project_number = "123456789012"          # 项目编号
state = "ACTIVE"                         # 项目状态

[[accounts.projects]]
project_id = "my-project-456"
project_name = "My Second Project"
project_number = "123456789013"
state = "ACTIVE"
```

## 示例完整文件

```toml
[[accounts]]
access_token = "ya29.a0AfB_byABcDefGhI..."
refresh_token = "1//0gXXXXXXXXXXXXXXX..."
expires_in = 3599
token_type = "Bearer"
scope = "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email..."
timestamp = 1732531200000
created_at = "2025-11-25 18:00:00"
last_used = "2025-11-25 18:00:00"
enable = true
email = "developer@gmail.com"
name = "Developer Zhang"
picture = "https://lh3.googleusercontent.com/a/ACg8ocJ..."
verified_email = true
user_id = "123456789012345678901"
locale = "zh-CN"
project_count = 2

[[accounts.projects]]
project_id = "antigravity-test-123"
project_name = "Antigravity Test Project"
project_number = "987654321098"
state = "ACTIVE"

[[accounts.projects]]
project_id = "my-ai-project-456"
project_name = "My AI Assistant"
project_number = "987654321099"
state = "ACTIVE"

# 可以有多个账户
[[accounts]]
access_token = "ya29.a0AfB_byANOTHER..."
refresh_token = "1//0gYYYYYYYYYYYYYYY..."
expires_in = 3599
token_type = "Bearer"
scope = "https://www.googleapis.com/auth/cloud-platform..."
timestamp = 1732534800000
created_at = "2025-11-25 19:00:00"
last_used = "2025-11-25 19:00:00"
enable = true
email = "another@gmail.com"
name = "Another User"
picture = "https://lh3.googleusercontent.com/a/ACg8ocK..."
verified_email = true
user_id = "098765432109876543210"
locale = "en-US"
project_count = 1

[[accounts.projects]]
project_id = "test-project-789"
project_name = "Test Project"
project_number = "111222333444"
state = "ACTIVE"
```

## 新增功能特性

### ✅ 自动获取的信息

1. **用户身份信息**
   - 邮箱地址（用于识别和去重）
   - 用户真实姓名
   - 头像 URL
   - 邮箱验证状态

2. **项目关联信息**
   - 自动获取用户有权限的所有 Google Cloud 项目
   - 保存前 10 个项目的详细信息
   - 记录项目总数

3. **时间追踪**
   - 创建时间（人类可读格式）
   - 最后使用时间
   - Unix 时间戳（用于程序计算）

### ✅ 智能去重

系统会自动检测相同邮箱的账户：
- 如果检测到相同邮箱，会**自动删除旧凭证**
- 只保留最新的凭证
- 避免重复账户造成混乱

### ✅ 日志输出示例

```
INFO - 开始交换 Token...
INFO - Token 交换成功，开始获取用户信息...
INFO - 成功获取用户信息: developer@gmail.com
INFO - 📧 账户邮箱: developer@gmail.com
INFO - 👤 用户名称: Developer Zhang
INFO - 成功获取 2 个项目信息
INFO - 📁 关联项目数: 2 个
INFO - 📁 首个项目: Antigravity Test Project (antigravity-test-123)
INFO - ✨ 已移除邮箱 developer@gmail.com 的旧凭证（如有）
INFO - ✅ 凭证已保存到 D:\Research\fandai\2apifare\creds\accounts.toml
INFO - 📊 当前共有 1 个账户
```

## 使用场景

### 1. 账户管理
通过邮箱快速识别不同的 Google 账户，避免混淆。

### 2. 项目切换
查看每个账户关联的项目，方便选择合适的项目使用。

### 3. 调试追踪
通过创建时间和最后使用时间追踪凭证的使用情况。

### 4. 多账户支持
支持保存多个 Google 账户的凭证，自动轮换使用。

## 对比旧版格式

### 旧版（只有基础信息）
```toml
[[accounts]]
access_token = "..."
refresh_token = "..."
expires_in = 3599
timestamp = 1732531200000
enable = true
```

### 新版（丰富信息）
```toml
[[accounts]]
access_token = "..."
refresh_token = "..."
expires_in = 3599
token_type = "Bearer"
scope = "..."
timestamp = 1732531200000
created_at = "2025-11-25 18:00:00"
last_used = "2025-11-25 18:00:00"
enable = true

# 新增：用户信息
email = "user@gmail.com"
name = "张三"
picture = "https://..."
verified_email = true
user_id = "123..."
locale = "zh-CN"

# 新增：项目信息
project_count = 2

[[accounts.projects]]
project_id = "project-123"
project_name = "My Project"
project_number = "987654321"
state = "ACTIVE"
```

## 总结

新版凭证格式提供了：
- 📧 **完整的用户身份信息**
- 📁 **关联的项目列表**
- ⏰ **时间追踪功能**
- 🔄 **自动去重机制**
- 📊 **更好的可读性和可维护性**

这些信息对于管理多个账户、调试问题、追踪使用情况都非常有帮助！
