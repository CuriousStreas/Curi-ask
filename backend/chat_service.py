"""
聊天服务模块。
提供统一的聊天接口，自动路由到合适的模型提供商。
"""
import logging
from typing import Dict, Any, Generator, List, Optional

from providers import get_provider

logger = logging.getLogger(__name__)


def chat_completion(
    model: str, 
    messages: List[Dict[str, str]], 
    images: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    非流式对话（保留兼容）。
    
    Args:
        model: 模型 ID
        messages: 消息列表
        images: 可选的图片列表，每个元素包含 mime_type 和 data (base64)
        
    Returns:
        包含 content, role, model 的响应字典
    """
    provider = get_provider(model)
    
    # 检查提供商是否支持图片参数
    if images and hasattr(provider, 'chat_completion'):
        import inspect
        sig = inspect.signature(provider.chat_completion)
        if 'images' in sig.parameters:
            return provider.chat_completion(model, messages, images=images)
    
    return provider.chat_completion(model, messages)


def chat_completion_stream(
    model: str, 
    messages: List[Dict[str, str]], 
    images: Optional[List[Dict[str, str]]] = None
) -> Generator[str, None, None]:
    """
    流式对话。
    
    Args:
        model: 模型 ID
        messages: 消息列表
        images: 可选的图片列表，每个元素包含 mime_type 和 data (base64)
        
    Yields:
        SSE 格式数据
    """
    provider = get_provider(model)
    
    # 检查提供商是否支持图片参数
    if images and hasattr(provider, 'chat_completion_stream'):
        import inspect
        sig = inspect.signature(provider.chat_completion_stream)
        if 'images' in sig.parameters:
            yield from provider.chat_completion_stream(model, messages, images=images)
            return
    
    yield from provider.chat_completion_stream(model, messages)