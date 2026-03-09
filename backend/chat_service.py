"""
聊天服务模块。
提供统一的聊天接口，自动路由到合适的模型提供商。
"""
import logging
from typing import Dict, Any, Generator, List

from providers import get_provider

logger = logging.getLogger(__name__)


def chat_completion(model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    非流式对话（保留兼容）。
    
    Args:
        model: 模型 ID
        messages: 消息列表
        
    Returns:
        包含 content, role, model 的响应字典
    """
    provider = get_provider(model)
    return provider.chat_completion(model, messages)


def chat_completion_stream(model: str, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    流式对话。
    
    Args:
        model: 模型 ID
        messages: 消息列表
        
    Yields:
        SSE 格式数据
    """
    provider = get_provider(model)
    yield from provider.chat_completion_stream(model, messages)
