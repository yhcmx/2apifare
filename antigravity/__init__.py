"""
Antigravity 模块 - Google OAuth 认证和 API 调用
"""

from .auth import (
    generate_auth_url,
    exchange_code_for_token,
    get_user_info,
    get_project_info,
    save_credentials
)

from .converter import (
    generate_request_body,
    openai_messages_to_antigravity,
    convert_openai_tools_to_antigravity
)

from .client import (
    stream_generate_content,
    get_available_models,
    convert_sse_to_openai_format,
    generate_finish_chunk
)

__all__ = [
    # 认证相关
    'generate_auth_url',
    'exchange_code_for_token',
    'get_user_info',
    'get_project_info',
    'save_credentials',

    # 格式转换
    'generate_request_body',
    'openai_messages_to_antigravity',
    'convert_openai_tools_to_antigravity',

    # API 调用
    'stream_generate_content',
    'get_available_models',
    'convert_sse_to_openai_format',
    'generate_finish_chunk'
]
