# Antigravity Pro 账号支持功能实现方案

> 参考社区项目：antigravity2api-nodejs
> 更新时间：2025-12-06
> 状态：待实现

## 📋 功能概述

实现 4 个核心功能，完善 Antigravity Pro 账号支持：

1. ✅ **跳过项目检测配置** - Pro 账号可直接使用，无需 API 验证
2. ✅ **自动生成 projectId** - 简化 Pro 账号配置流程
3. ✅ **账号验证 API** - 添加账号时自动验证资格
4. ✅ **配置热更新** - 动态切换验证模式，无需重启

---

## 🎯 实现优先级

### Phase 1：核心配置功能（必须）
- [ ] 1. 添加跳过项目检测配置
- [ ] 2. 实现自动生成 projectId 逻辑

### Phase 2：账号管理功能（推荐）
- [ ] 3. 实现账号验证 API
- [ ] 4. 支持配置热更新

### Phase 3：UI 界面（可选）
- [ ] 5. 添加 Web 管理界面
- [ ] 6. 账号状态监控

---

## 📝 功能 1：跳过项目检测配置

### 实现目标

允许 Pro 账号跳过 `loadCodeAssist` API 验证，直接使用随机 projectId。

### 实现步骤

#### Step 1.1：添加配置项

**文件**：`config.py`

**位置**：在 Antigravity 配置区域添加

```python
# ============================================================================
# Antigravity Configuration
# ============================================================================

# 是否跳过 Antigravity 项目验证（Pro 账号可用）
# - True: 跳过验证，使用随机生成的 projectId（Pro 账号/家庭组共享号）
# - False: 需要 API 验证（免费账号，官方已修复随机 projectId 漏洞）
ANTIGRAVITY_SKIP_PROJECT_VERIFICATION = os.getenv(
    "ANTIGRAVITY_SKIP_PROJECT_VERIFICATION",
    "false"
).lower() == "true"


async def get_antigravity_skip_project_verification() -> bool:
    """
    获取 Antigravity 跳过项目验证配置

    Returns:
        bool: True 表示跳过验证（Pro 账号），False 表示需要验证（免费账号）
    """
    env_value = os.getenv("ANTIGRAVITY_SKIP_PROJECT_VERIFICATION")
    if env_value:
        return env_value.lower() in ("true", "1", "yes", "on")

    # 检查 TOML 配置
    value = await get_config_value("antigravity_skip_project_verification")
    if value is not None:
        return bool(value)

    return ANTIGRAVITY_SKIP_PROJECT_VERIFICATION
```

#### Step 1.2：更新环境变量示例

**文件**：`.env.example`

**添加内容**：
```env
# ============================================================================
# Antigravity Configuration
# ============================================================================

# 是否跳过项目验证（Pro 账号跳过，免费账号需要验证）
# Pro 账号/家庭组共享号：设为 true
# 免费账号：设为 false（需要 API 验证 projectId）
ANTIGRAVITY_SKIP_PROJECT_VERIFICATION=false
```

#### Step 1.3：更新 TOML 配置示例

**文件**：`config.toml.example` (如果存在)

```toml
[antigravity]
# 跳过项目验证（Pro 账号可用）
skip_project_verification = false
```

### 测试方法

```bash
# 测试配置读取
python -c "
import asyncio
from config import get_antigravity_skip_project_verification

async def test():
    result = await get_antigravity_skip_project_verification()
    print(f'Skip verification: {result}')

asyncio.run(test())
"
```

**预期输出**：
```
Skip verification: False  # 默认值
```

---

## 📝 功能 2：自动生成 projectId 逻辑

### 实现目标

在凭证管理器中，根据配置自动生成或验证 projectId。

### 实现步骤

#### Step 2.1：确认生成函数已存在

**检查文件**：`antigravity/converter.py`

确认以下函数存在（已有）：
```python
def generate_project_id() -> str:
    """生成项目 ID"""
    adjectives = ['useful', 'bright', 'swift', 'calm', 'bold']
    nouns = ['fuze', 'wave', 'spark', 'flow', 'core']
    random_adj = random.choice(adjectives)
    random_noun = random.choice(nouns)
    random_str = uuid.uuid4().hex[:5]
    return f"{random_adj}-{random_noun}-{random_str}"
```

✅ **已确认存在**，无需修改。

#### Step 2.2：修改凭证管理器

**文件**：`src/antigravity_credential_manager.py`

**位置**：在 `get_valid_credential()` 方法中添加逻辑

```python
async def get_valid_credential(self, model_name: str = None, _checked_count: int = 0) -> Optional[Dict[str, Any]]:
    """
    获取有效的凭证，自动处理轮换和失效凭证切换

    Args:
        model_name: 模型名称（用于配额检查和系列封禁检查）
        _checked_count: 内部参数，已检查的账号数量（防止死循环）

    Returns:
        Dict with 'account' and 'virtual_filename' keys, or None if no valid credential
    """
    async with self._operation_lock:
        if not self._credential_accounts:
            await self._discover_credentials()
            if not self._credential_accounts:
                return None

        # [FIX] 防止死循环：如果已检查账号数超过总账号数，说明所有账号都不可用
        if _checked_count >= len(self._credential_accounts):
            log.error(f"All {len(self._credential_accounts)} Antigravity accounts checked, none available for model {model_name}")
            return None

        # 检查是否需要轮换（基于调用次数）
        if await self._should_rotate():
            await self._rotate_credential()

        # 如果当前没有加载凭证，加载第一个
        if not self._current_credential_account:
            await self._load_current_credential()

        # ===== [NEW] 检查并处理 projectId =====
        if self._current_credential_account:
            await self._ensure_project_id(self._current_credential_account)

        # 检查系列级临时封禁（如果提供了模型名称）
        if model_name and self._current_credential_account:
            is_banned = await self._check_series_ban(self._current_credential_account, model_name)

            if is_banned:
                # 系列被封禁，切换到下一个账号
                if len(self._credential_accounts) > 1:
                    log.info(f"Rotating to next account due to series ban (checked {_checked_count + 1}/{len(self._credential_accounts)})")
                    await self._rotate_credential()
                    await self._load_current_credential()

                    # 递归调用检查新账号，增加检查计数
                    return await self.get_valid_credential(model_name, _checked_count + 1)
                else:
                    log.error("Only one account available and series is banned")
                    return None

        # 检查 token 是否过期，如果过期则刷新
        if self._current_credential_account:
            if self._is_token_expired(self._current_credential_account):
                log.info("Current token expired, refreshing...")

                refresh_success = await self._refresh_access_token(self._current_credential_account)

                if not refresh_success:
                    # 刷新失败，禁用当前账号并尝试下一个
                    log.warning(f"Failed to refresh token for {self._current_credential_account.get('email')}, disabling account")

                    virtual_filename = self._credential_accounts[self._current_credential_index]["virtual_filename"]
                    await self.disable_credential(virtual_filename)

                    # 重新加载凭证列表
                    await self._discover_credentials()

                    if not self._credential_accounts:
                        log.error("No valid Antigravity credentials remaining after refresh failure")
                        return None

                    # 尝试下一个账号
                    await self._load_current_credential()

                    if self._current_credential_account:
                        # 递归调用以确保新账号也是有效的，增加检查计数
                        return await self.get_valid_credential(model_name, _checked_count + 1)
                    else:
                        return None

        # 返回当前凭证
        if self._current_credential_account:
            return {
                "account": self._current_credential_account,
                "virtual_filename": self._credential_accounts[self._current_credential_index][
                    "virtual_filename"
                ],
            }

        return None


async def _ensure_project_id(self, account: Dict[str, Any]) -> None:
    """
    确保账号有 projectId，如果没有则根据配置生成或验证

    Args:
        account: 账号数据字典
    """
    from config import get_antigravity_skip_project_verification
    from antigravity.converter import generate_project_id

    # 检查是否已有 projectId
    if 'project_id' in account and account['project_id']:
        return  # 已有，无需处理

    # 获取配置
    skip_verification = await get_antigravity_skip_project_verification()

    if skip_verification:
        # ===== Pro 账号模式：生成随机 projectId =====
        account['project_id'] = generate_project_id()
        log.info(f"[Pro Account] Generated random projectId: {account['project_id']} for {account.get('email', 'unknown')}")

        # 保存到存储
        await self._save_account_to_storage(account)

    else:
        # ===== 免费账号模式：API 验证获取 projectId =====
        log.info(f"[Free Account] Fetching projectId from API for {account.get('email', 'unknown')}")

        try:
            project_id = await self._fetch_project_id_from_api(account)

            if not project_id:
                log.warning(f"Account {account.get('email', 'unknown')} has no Antigravity access (projectId not found)")
                # 标记账号无资格，但不禁用（可能是临时问题）
                account['has_antigravity_access'] = False
                return

            account['project_id'] = project_id
            account['has_antigravity_access'] = True
            log.info(f"[Free Account] ProjectId verified: {project_id}")

            # 保存到存储
            await self._save_account_to_storage(account)

        except Exception as e:
            log.error(f"Failed to fetch projectId from API: {e}")
            # 验证失败，使用随机 projectId 作为降级方案（可能会失败）
            account['project_id'] = generate_project_id()
            log.warning(f"[Fallback] Using random projectId due to API error: {account['project_id']}")


async def _fetch_project_id_from_api(self, account: Dict[str, Any]) -> Optional[str]:
    """
    从 Google API 获取 projectId

    Args:
        account: 账号数据字典

    Returns:
        projectId 或 None（如果账号无资格）
    """
    try:
        # 调用 loadCodeAssist API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:loadCodeAssist',
                headers={
                    'Host': 'daily-cloudcode-pa.sandbox.googleapis.com',
                    'User-Agent': 'antigravity/1.11.9 windows/amd64',
                    'Authorization': f"Bearer {account['access_token']}",
                    'Content-Type': 'application/json',
                    'Accept-Encoding': 'gzip'
                },
                json={'metadata': {'ideType': 'ANTIGRAVITY'}}
            )

        if response.status_code == 200:
            data = response.json()
            project_id = data.get('cloudaicompanionProject')
            return project_id

        elif response.status_code == 403:
            log.warning(f"Account {account.get('email')} has no permission (403)")
            return None

        elif response.status_code == 404:
            log.warning(f"Account {account.get('email')} not found (404)")
            return None

        else:
            log.error(f"Unexpected status code {response.status_code}: {response.text}")
            return None

    except Exception as e:
        log.error(f"Error fetching projectId: {e}")
        raise


async def _save_account_to_storage(self, account: Dict[str, Any]) -> None:
    """
    保存账号数据到存储

    Args:
        account: 账号数据字典
    """
    try:
        virtual_filename = None

        # 查找对应的 virtual_filename
        for acc in self._credential_accounts:
            if acc.get('email') == account.get('email'):
                virtual_filename = acc.get('virtual_filename')
                break

        if not virtual_filename:
            log.error(f"Cannot find virtual_filename for account {account.get('email')}")
            return

        # 更新存储
        await self._storage_adapter.update_antigravity_account(virtual_filename, account)
        log.debug(f"Account data saved: {account.get('email')}")

    except Exception as e:
        log.error(f"Error saving account to storage: {e}")
```

#### Step 2.3：添加导入

**文件**：`src/antigravity_credential_manager.py` 顶部

```python
from antigravity.converter import generate_project_id
```

### 测试方法

```python
# 测试文件：test_project_id.py

import asyncio
import os
from src.antigravity_credential_manager import AntigravityCredentialManager

async def test_project_id_generation():
    # 设置跳过验证
    os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = 'true'

    mgr = AntigravityCredentialManager()

    # 模拟账号（没有 project_id）
    test_account = {
        'email': 'test@example.com',
        'access_token': 'ya29.test',
        'refresh_token': '1//test'
    }

    # 调用确保 projectId
    await mgr._ensure_project_id(test_account)

    # 检查结果
    assert 'project_id' in test_account
    assert test_account['project_id'] is not None
    assert '-' in test_account['project_id']  # 格式检查

    print(f"✅ Generated projectId: {test_account['project_id']}")

if __name__ == '__main__':
    asyncio.run(test_project_id_generation())
```

**运行**：
```bash
python test_project_id.py
```

**预期输出**：
```
✅ Generated projectId: useful-fuze-a3b2c
```

---

## 📝 功能 3：账号验证 API

### 实现目标

提供 HTTP API 端点，用于添加账号前验证资格。

### 实现步骤

#### Step 3.1：创建验证 API 路由

**新建文件**：`src/routes/antigravity_admin.py`

```python
"""
Antigravity 账号管理 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx

from config import get_antigravity_skip_project_verification
from antigravity.converter import generate_project_id
from antigravity.auth import exchange_code_for_token
from src.antigravity_credential_manager import get_antigravity_credential_manager
from log import log

router = APIRouter(prefix="/api/antigravity", tags=["Antigravity Admin"])


class VerifyAccountRequest(BaseModel):
    """验证账号请求"""
    code: str  # OAuth authorization code
    redirect_uri: str  # OAuth 重定向 URI


class VerifyAccountResponse(BaseModel):
    """验证账号响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.post("/accounts/verify", response_model=VerifyAccountResponse)
async def verify_account(request: VerifyAccountRequest):
    """
    验证 Antigravity 账号资格

    流程：
    1. 使用 authorization_code 交换 token
    2. 根据配置决定是否验证 projectId
    3. 返回账号数据（包含 projectId）
    """
    try:
        # Step 1: 交换 token
        log.info(f"Exchanging code for token...")

        token_data = await exchange_code_for_token(request.code, request.redirect_uri)

        if not token_data.get('access_token'):
            raise HTTPException(status_code=400, detail="Token exchange failed")

        # 构造账号数据
        account = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data.get('expires_in', 3599),
            'token_expiry': token_data.get('token_expiry'),
            'email': None,  # 后续可以从 userinfo API 获取
            'enable': True
        }

        # Step 2: 获取配置
        skip_verification = await get_antigravity_skip_project_verification()

        if skip_verification:
            # ===== Pro 账号模式：生成随机 projectId =====
            account['project_id'] = generate_project_id()
            log.info(f"[Pro Account Mode] Generated random projectId: {account['project_id']}")

        else:
            # ===== 免费账号模式：API 验证 =====
            log.info("[Free Account Mode] Verifying projectId via API...")

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        'https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:loadCodeAssist',
                        headers={
                            'Host': 'daily-cloudcode-pa.sandbox.googleapis.com',
                            'User-Agent': 'antigravity/1.11.9 windows/amd64',
                            'Authorization': f"Bearer {account['access_token']}",
                            'Content-Type': 'application/json',
                            'Accept-Encoding': 'gzip'
                        },
                        json={'metadata': {'ideType': 'ANTIGRAVITY'}}
                    )

                if response.status_code == 200:
                    data = response.json()
                    project_id = data.get('cloudaicompanionProject')

                    if not project_id:
                        return VerifyAccountResponse(
                            success=False,
                            message="该账号无资格使用 Antigravity（无法获取 projectId）"
                        )

                    account['project_id'] = project_id
                    log.info(f"Account verified, projectId: {project_id}")

                elif response.status_code == 403:
                    return VerifyAccountResponse(
                        success=False,
                        message="该账号无权限访问 Antigravity API (403 Forbidden)"
                    )

                elif response.status_code == 404:
                    return VerifyAccountResponse(
                        success=False,
                        message="该账号未开通 Antigravity 服务 (404 Not Found)"
                    )

                else:
                    return VerifyAccountResponse(
                        success=False,
                        message=f"API 验证失败 ({response.status_code}): {response.text[:200]}"
                    )

            except httpx.TimeoutException:
                return VerifyAccountResponse(
                    success=False,
                    message="验证超时，请检查网络连接"
                )

            except Exception as e:
                log.error(f"Error verifying account: {e}")
                return VerifyAccountResponse(
                    success=False,
                    message=f"验证失败: {str(e)}"
                )

        # Step 3: 返回验证结果
        return VerifyAccountResponse(
            success=True,
            message="账号验证成功",
            data=account
        )

    except HTTPException:
        raise

    except Exception as e:
        log.error(f"Unexpected error in verify_account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddAccountRequest(BaseModel):
    """添加账号请求"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_expiry: Optional[str] = None
    project_id: str
    email: Optional[str] = None
    enable: bool = True


@router.post("/accounts/add")
async def add_account(request: AddAccountRequest):
    """
    添加 Antigravity 账号

    注意：调用此 API 前应先调用 /verify 验证账号
    """
    try:
        mgr = await get_antigravity_credential_manager()

        # 构造账号数据
        account_data = request.dict()

        # 保存账号
        await mgr.add_account(account_data)

        log.info(f"Account added: {account_data.get('email', 'unknown')}")

        return {
            "success": True,
            "message": "账号添加成功"
        }

    except Exception as e:
        log.error(f"Error adding account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/list")
async def list_accounts():
    """
    获取所有 Antigravity 账号列表
    """
    try:
        mgr = await get_antigravity_credential_manager()

        accounts = []
        for acc in mgr._credential_accounts:
            accounts.append({
                'email': acc.get('email'),
                'project_id': acc.get('project_id'),
                'enable': acc.get('enable', True),
                'virtual_filename': acc.get('virtual_filename')
            })

        return {
            "success": True,
            "data": accounts
        }

    except Exception as e:
        log.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Step 3.2：注册路由

**文件**：`main.py` 或主应用文件

```python
from src.routes.antigravity_admin import router as antigravity_admin_router

# 在 FastAPI 应用中注册路由
app.include_router(antigravity_admin_router)
```

### 测试方法

```bash
# 测试验证 API
curl -X POST http://localhost:8000/api/antigravity/accounts/verify \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AfJohXl...",
    "redirect_uri": "http://localhost:8000/callback"
  }'
```

**预期响应**（跳过验证模式）：
```json
{
  "success": true,
  "message": "账号验证成功",
  "data": {
    "access_token": "ya29.xxx",
    "refresh_token": "1//xxx",
    "expires_in": 3599,
    "project_id": "useful-fuze-a3b2c",
    "enable": true
  }
}
```

---

## 📝 功能 4：配置热更新

### 实现目标

允许动态修改配置，无需重启服务。

### 实现步骤

#### Step 4.1：创建配置管理 API

**文件**：`src/routes/config_admin.py`

```python
"""
配置管理 API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import os
import toml

from config import get_config_value, set_config_value
from log import log

router = APIRouter(prefix="/api/config", tags=["Config Admin"])


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    antigravity_skip_project_verification: bool


@router.get("/current")
async def get_current_config():
    """
    获取当前配置
    """
    try:
        from config import get_antigravity_skip_project_verification

        config = {
            'antigravity_skip_project_verification': await get_antigravity_skip_project_verification()
        }

        return {
            "success": True,
            "data": config
        }

    except Exception as e:
        log.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update")
async def update_config(request: UpdateConfigRequest):
    """
    更新配置（热更新，无需重启）

    支持更新的配置项：
    - antigravity_skip_project_verification: bool
    """
    try:
        # Step 1: 更新环境变量
        os.environ['ANTIGRAVITY_SKIP_PROJECT_VERIFICATION'] = str(request.antigravity_skip_project_verification).lower()

        # Step 2: 更新 .env 文件（持久化）
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('ANTIGRAVITY_SKIP_PROJECT_VERIFICATION='):
                    lines[i] = f"ANTIGRAVITY_SKIP_PROJECT_VERIFICATION={str(request.antigravity_skip_project_verification).lower()}\n"
                    updated = True
                    break

            if not updated:
                lines.append(f"\nANTIGRAVITY_SKIP_PROJECT_VERIFICATION={str(request.antigravity_skip_project_verification).lower()}\n")

            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            log.info(f".env file updated: ANTIGRAVITY_SKIP_PROJECT_VERIFICATION={request.antigravity_skip_project_verification}")

        # Step 3: 更新 config.toml（如果存在）
        config_file = 'config.toml'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = toml.load(f)

                if 'antigravity' not in config_data:
                    config_data['antigravity'] = {}

                config_data['antigravity']['skip_project_verification'] = request.antigravity_skip_project_verification

                with open(config_file, 'w', encoding='utf-8') as f:
                    toml.dump(config_data, f)

                log.info(f"config.toml updated")

            except Exception as e:
                log.warning(f"Failed to update config.toml: {e}")

        # Step 4: 返回成功
        log.info(f"✅ Configuration updated successfully: skip_project_verification={request.antigravity_skip_project_verification}")

        return {
            "success": True,
            "message": "配置更新成功（已生效，无需重启）",
            "data": {
                "antigravity_skip_project_verification": request.antigravity_skip_project_verification
            }
        }

    except Exception as e:
        log.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Step 4.2：注册路由

**文件**：`main.py`

```python
from src.routes.config_admin import router as config_admin_router

app.include_router(config_admin_router)
```

### 测试方法

```bash
# 1. 获取当前配置
curl http://localhost:8000/api/config/current

# 2. 更新配置（开启跳过验证）
curl -X PUT http://localhost:8000/api/config/update \
  -H "Content-Type: application/json" \
  -d '{
    "antigravity_skip_project_verification": true
  }'

# 3. 验证配置已更新
curl http://localhost:8000/api/config/current
```

**预期响应**：
```json
{
  "success": true,
  "message": "配置更新成功（已生效，无需重启）",
  "data": {
    "antigravity_skip_project_verification": true
  }
}
```

---

## 🧪 集成测试

### 完整流程测试

```python
# test_antigravity_pro.py

import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_full_workflow():
    """测试完整的 Pro 账号添加流程"""

    async with httpx.AsyncClient() as client:
        # Step 1: 开启跳过验证
        print("1️⃣ 开启跳过验证模式...")
        response = await client.put(
            f"{BASE_URL}/api/config/update",
            json={"antigravity_skip_project_verification": True}
        )
        assert response.json()['success']
        print("✅ 配置已更新")

        # Step 2: 验证账号（使用测试 code）
        print("\n2️⃣ 验证测试账号...")
        # 注意：这里需要真实的 OAuth code
        # response = await client.post(
        #     f"{BASE_URL}/api/antigravity/accounts/verify",
        #     json={
        #         "code": "4/0AfJohXl...",
        #         "redirect_uri": "http://localhost:8000/callback"
        #     }
        # )
        # assert response.json()['success']
        # account_data = response.json()['data']
        # print(f"✅ 账号验证成功，projectId: {account_data['project_id']}")

        # Step 3: 获取配置确认
        print("\n3️⃣ 确认配置...")
        response = await client.get(f"{BASE_URL}/api/config/current")
        config = response.json()['data']
        assert config['antigravity_skip_project_verification'] == True
        print("✅ 配置确认：跳过验证已开启")

        print("\n🎉 所有测试通过！")

if __name__ == '__main__':
    asyncio.run(test_full_workflow())
```

---

## 📋 实现检查清单

### Phase 1：核心配置

- [ ] **配置项**
  - [ ] `config.py` 添加 `ANTIGRAVITY_SKIP_PROJECT_VERIFICATION`
  - [ ] 添加 `get_antigravity_skip_project_verification()` 函数
  - [ ] `.env.example` 添加配置说明
  - [ ] 测试配置读取

- [ ] **projectId 逻辑**
  - [ ] 确认 `generate_project_id()` 函数存在
  - [ ] 在凭证管理器添加 `_ensure_project_id()` 方法
  - [ ] 在凭证管理器添加 `_fetch_project_id_from_api()` 方法
  - [ ] 在凭证管理器添加 `_save_account_to_storage()` 方法
  - [ ] 在 `get_valid_credential()` 中调用 `_ensure_project_id()`
  - [ ] 测试生成和验证逻辑

### Phase 2：账号管理

- [ ] **验证 API**
  - [ ] 创建 `src/routes/antigravity_admin.py`
  - [ ] 实现 `POST /api/antigravity/accounts/verify`
  - [ ] 实现 `POST /api/antigravity/accounts/add`
  - [ ] 实现 `GET /api/antigravity/accounts/list`
  - [ ] 在 `main.py` 注册路由
  - [ ] 测试 API 端点

- [ ] **配置热更新**
  - [ ] 创建 `src/routes/config_admin.py`
  - [ ] 实现 `GET /api/config/current`
  - [ ] 实现 `PUT /api/config/update`
  - [ ] 在 `main.py` 注册路由
  - [ ] 测试热更新功能

### Phase 3：文档和测试

- [ ] **文档**
  - [ ] 更新 README.md 添加功能说明
  - [ ] 添加 API 文档
  - [ ] 添加配置示例

- [ ] **测试**
  - [ ] 单元测试：projectId 生成
  - [ ] 单元测试：配置读取
  - [ ] 集成测试：完整流程
  - [ ] 手动测试：Pro 账号添加
  - [ ] 手动测试：免费账号验证失败

---

## ⚠️ 注意事项

### 安全考虑

1. **API 认证**：所有管理 API 应该添加认证中间件
2. **配置验证**：更新配置前验证值的有效性
3. **敏感信息**：不要在日志中输出完整的 token

### 兼容性

1. **向后兼容**：确保旧账号（已有 projectId）不受影响
2. **降级方案**：API 验证失败时使用随机 projectId（可能会失败）
3. **错误处理**：所有 API 调用都要有完善的错误处理

### 性能优化

1. **缓存**：projectId 一旦获取成功应该缓存
2. **超时**：API 调用设置合理的超时时间
3. **并发**：多个账号同时验证时避免竞态条件

---

## 🚀 部署建议

### 生产环境配置

```env
# .env 生产环境
ANTIGRAVITY_SKIP_PROJECT_VERIFICATION=true  # Pro 账号环境
```

### 免费账号环境配置

```env
# .env 免费账号环境
ANTIGRAVITY_SKIP_PROJECT_VERIFICATION=false  # 需要 API 验证
```

### 混合环境

如果同时有 Pro 账号和免费账号，建议：
1. 默认开启跳过验证（`true`）
2. 为免费账号单独标记并特殊处理
3. 或使用两个独立的服务实例

---

## 📚 参考资料

- 社区项目：`docs/antigravity2api-nodejs`
- Google OAuth 文档：https://developers.google.com/identity/protocols/oauth2
- Antigravity API 文档：（内部文档）

---

## 🔄 更新日志

### 2025-12-06
- 创建实现方案文档
- 定义 4 个核心功能
- 编写详细实现步骤

---

## ✅ 完成标准

所有功能实现完成后，应该能够：

1. ✅ Pro 账号无需 API 验证，直接使用
2. ✅ 免费账号自动调用 API 验证
3. ✅ 通过 API 添加和验证账号
4. ✅ 动态切换验证模式，无需重启
5. ✅ 所有测试通过

开始实现吧！🎉
