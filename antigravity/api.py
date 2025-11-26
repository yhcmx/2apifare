from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .auth import generate_auth_url, exchange_code_for_token, save_credentials, get_user_info
import logging

router = APIRouter()
log = logging.getLogger("antigravity.api")

class AuthStartRequest(BaseModel):
    redirect_uri: str = "http://localhost:8080/oauth-callback" # 默认值，前端可以覆盖

class AuthExchangeRequest(BaseModel):
    callback_url: str

@router.post("/auth/start")
async def start_auth(request: AuthStartRequest = Body(...)):
    """生成 Antigravity 认证链接"""
    try:
        auth_url = generate_auth_url(request.redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        log.error(f"Failed to generate auth url: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/exchange")
async def exchange_token(request: AuthExchangeRequest = Body(...)):
    """从回调 URL 获取 Token 并保存（增强版）"""
    try:
        # 解析 callback_url 获取 code
        from urllib.parse import urlparse, parse_qs

        parsed_url = urlparse(request.callback_url)
        query_params = parse_qs(parsed_url.query)

        code = query_params.get('code', [None])[0]
        if not code:
            raise HTTPException(status_code=400, detail="No code found in callback URL")

        # 构造 redirect_uri (需要与生成链接时一致)
        redirect_uri = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        log.info(f"开始交换 Token...")

        # 交换 Token
        token_data = await exchange_code_for_token(code, redirect_uri)

        log.info(f"Token 交换成功，开始获取用户信息...")

        # 获取用户信息以便在响应中返回
        user_info = await get_user_info(token_data.get('access_token'))

        # 保存凭证（现在是异步函数，会自动获取用户信息和项目信息）
        if await save_credentials(token_data, user_info):
            response_data = {
                "message": "✅ Antigravity 认证成功！已保存用户信息、邮箱和项目信息。",
                "success": True
            }

            # 如果成功获取用户信息，添加到响应中
            if user_info:
                response_data["user_info"] = {
                    "email": user_info.get('email', ''),
                    "name": user_info.get('name', ''),
                    "picture": user_info.get('picture', ''),
                    "verified_email": user_info.get('verified_email', False)
                }

            return response_data
        else:
            raise HTTPException(status_code=500, detail="Failed to save credentials")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Auth exchange failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
