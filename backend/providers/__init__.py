"""
模型提供商模块。
支持多种 AI 模型提供商，统一接口调用。

使用方式:
    from providers import init_registry, get_provider
    
    # 初始化（应用启动时调用一次）
    init_registry(base_url="https://api.example.com", api_key="sk-xxx")
    
    # 获取提供商并调用
    provider = get_provider("gemini-2.5-pro")
    result = provider.chat_completion(model, messages)
"""
from .base import BaseProvider
from .openai_compatible import OpenAICompatibleProvider
from .gemini import GeminiProvider, GEMINI_MODELS
from .nano_banana import NanoBananaProvider, NANO_BANANA_MODELS
from .registry import (
    ProviderRegistry,
    init_registry,
    get_registry,
    get_provider,
)

__all__ = [
    "BaseProvider",
    "OpenAICompatibleProvider",
    "GeminiProvider",
    "GEMINI_MODELS",
    "NanoBananaProvider",
    "NANO_BANANA_MODELS",
    "ProviderRegistry",
    "init_registry",
    "get_registry",
    "get_provider",
]