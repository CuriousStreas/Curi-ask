"""
Google Gemini 模型提供商。
通过 OpenAI 兼容接口调用 Gemini 系列模型。

支持的模型:
- gemini-pro-latest: 最新版 Gemini Pro
- gemini-pro-latest-thinking-*: 带思考链的 Gemini Pro
- gemini-flash-latest: 最新版 Gemini Flash (更快速)
- gemini-2.5-pro: Gemini 2.5 Pro
- gemini-2.5-flash: Gemini 2.5 Flash
"""
import logging
from typing import List, Dict, Any, Generator

from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class GeminiProvider(OpenAICompatibleProvider):
    """
    Google Gemini 模型提供商。
    基于 OpenAI 兼容接口，针对 Gemini 模型做了优化。
    """
    
    name = "gemini"
    
    # Gemini 系列模型前缀
    supported_models = [
        "gemini-",
    ]
    
    # 模型别名映射（可选，用于简化模型名称）
    MODEL_ALIASES = {
        "gemini-pro": "gemini-pro-latest",
        "gemini-flash": "gemini-flash-latest",
    }
    
    # 支持思考链的模型
    THINKING_MODELS = [
        "gemini-pro-latest-thinking",
        "gemini-2.5-pro-thinking",
    ]
    
    def __init__(self, base_url: str, api_key: str = None, **kwargs):
        """
        初始化 Gemini 提供商。
        
        Args:
            base_url: API 基础地址（如聚合 API 地址）
            api_key: API 密钥
            **kwargs: 其他配置
        """
        # Gemini 通过聚合 API 使用 OpenAI 兼容格式
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            chat_path="/v1/chat/completions",
            **kwargs
        )
    
    def _resolve_model(self, model: str) -> str:
        """解析模型别名"""
        return self.MODEL_ALIASES.get(model, model)
    
    def _is_thinking_model(self, model: str) -> bool:
        """检查是否为思考链模型"""
        for prefix in self.THINKING_MODELS:
            if model.startswith(prefix):
                return True
        return False
    
    def _build_payload(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> dict:
        """
        构建请求体。
        Gemini 思考链模型可能需要特殊处理。
        """
        resolved_model = self._resolve_model(model)
        payload = super()._build_payload(resolved_model, messages, stream)
        
        # 思考链模型可能需要额外参数（根据实际 API 调整）
        if self._is_thinking_model(resolved_model):
            logger.debug(f"使用思考链模型: {resolved_model}")
        
        return payload
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """非流式对话"""
        resolved_model = self._resolve_model(model)
        logger.info(f"[Gemini] 调用模型: {model} -> {resolved_model}")
        return super().chat_completion(resolved_model, messages)
    
    def chat_completion_stream(self, model: str, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """流式对话"""
        resolved_model = self._resolve_model(model)
        logger.info(f"[Gemini] 流式调用模型: {model} -> {resolved_model}")
        yield from super().chat_completion_stream(resolved_model, messages)


# 预定义的 Gemini 模型列表（严格按照聚合平台支持的模型名称）
GEMINI_MODELS = [
    {
        "id": "gemini-pro-latest",
        "name": "gemini-pro-latest",
        "description": "最新版 Gemini Pro",
    },
    {
        "id": "gemini-pro-latest-thinking-*",
        "name": "gemini-pro-latest-thinking-*",
        "description": "带思考链的 Gemini Pro（实验性）",
    },
    {
        "id": "gemini-flash-latest",
        "name": "gemini-flash-latest",
        "description": "最新版 Gemini Flash，速度最快",
    },
    {
        "id": "gemini-3-pro",
        "name": "gemini-3-pro",
        "description": "最新版 Gemini Flash，速度最快",
    },
]