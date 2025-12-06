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
                'email': acc.get('account', {}).get('email'),
                'project_id': acc.get('account', {}).get('project_id'),
                'enable': acc.get('account', {}).get('enable', True),
                'virtual_filename': acc.get('virtual_filename')
            })

        return {
            "success": True,
            "data": accounts
        }

    except Exception as e:
        log.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
