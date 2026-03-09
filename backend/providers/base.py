"""
提供商基类。
定义所有模型提供商必须实现的接口。
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """
    模型提供商基类。
    所有具体提供商必须继承此类并实现相关方法。
    """
    
    # 提供商名称
    name: str = "base"
    
    # 支持的模型列表（模型ID前缀或完整ID）
    supported_models: List[str] = []
    
    def __init__(self, base_url: str, api_key: str = None, **kwargs):
        """
        初始化提供商。
        
        Args:
            base_url: API 基础地址
            api_key: API 密钥
            **kwargs: 其他配置参数
        """
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def chat_completion(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        非流式对话。
        
        Args:
            model: 模型 ID
            messages: 消息列表，每个消息包含 role 和 content
            
        Returns:
            包含 content, role, model 的响应字典
        """
        pass
    
    @abstractmethod
    def chat_completion_stream(self, model: str, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        流式对话。
        
        Args:
            model: 模型 ID
            messages: 消息列表
            
        Yields:
            SSE 格式数据：data: {"content": "...", "model": "...", "done": false}\n\n
        """
        pass
    
    def supports_model(self, model: str) -> bool:
        """
        检查是否支持指定模型。
        
        Args:
            model: 模型 ID
            
        Returns:
            是否支持该模型
        """
        for prefix in self.supported_models:
            if model.startswith(prefix) or model == prefix:
                return True
        return False
    
    def _format_sse(self, data: dict) -> str:
        """格式化 SSE 数据"""
        return f'data: {json.dumps(data)}\n\n'
    
    def _format_error_sse(self, error: str) -> str:
        """格式化错误 SSE"""
        return self._format_sse({"error": error})
