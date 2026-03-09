"""
提供商注册表。
管理所有可用的模型提供商，根据模型自动选择合适的提供商。
"""
import logging
from typing import Dict, List, Optional, Type

from .base import BaseProvider
from .openai_compatible import OpenAICompatibleProvider
from .gemini import GeminiProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    提供商注册表。
    管理多个提供商实例，根据模型名称自动路由到对应提供商。
    """
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider: Optional[BaseProvider] = None
    
    def register(self, provider: BaseProvider, set_as_default: bool = False) -> None:
        """
        注册提供商。
        
        Args:
            provider: 提供商实例
            set_as_default: 是否设为默认提供商
        """
        self._providers[provider.name] = provider
        logger.info(f"注册提供商: {provider.name}")
        
        if set_as_default or self._default_provider is None:
            self._default_provider = provider
            logger.info(f"设置默认提供商: {provider.name}")
    
    def get_provider(self, model: str) -> BaseProvider:
        """
        根据模型获取对应的提供商。
        
        Args:
            model: 模型 ID
            
        Returns:
            支持该模型的提供商
            
        Raises:
            RuntimeError: 没有找到支持该模型的提供商
        """
        # 首先尝试找到支持该模型的专门提供商
        for provider in self._providers.values():
            if provider.supports_model(model):
                logger.debug(f"模型 {model} 使用提供商: {provider.name}")
                return provider
        
        # 使用默认提供商
        if self._default_provider:
            logger.debug(f"模型 {model} 使用默认提供商: {self._default_provider.name}")
            return self._default_provider
        
        raise RuntimeError(f"没有找到支持模型 {model} 的提供商")
    
    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """根据名称获取提供商"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """列出所有已注册的提供商名称"""
        return list(self._providers.keys())


# 全局注册表实例
_registry: Optional[ProviderRegistry] = None


def init_registry(base_url: str, api_key: str, chat_path: str = "/v1/chat/completions") -> ProviderRegistry:
    """
    初始化全局提供商注册表。
    
    Args:
        base_url: API 基础地址
        api_key: API 密钥
        chat_path: 聊天接口路径
        
    Returns:
        初始化后的注册表
    """
    global _registry
    _registry = ProviderRegistry()
    
    # 调试：打印配置（脱敏）
    key_len = len(api_key) if api_key else 0
    key_preview = f"长度={key_len}, 前缀={api_key[:3] if key_len >= 3 else 'N/A'}"
    logger.info(f"初始化注册表 - base_url: {base_url}, api_key: [{key_preview}], chat_path: {chat_path}")
    
    # 注册 Gemini 提供商（专门处理 gemini-* 模型）
    gemini_provider = GeminiProvider(
        base_url=base_url,
        api_key=api_key,
    )
    _registry.register(gemini_provider)
    
    # 注册通用 OpenAI 兼容提供商作为默认（处理其他所有模型）
    openai_provider = OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        chat_path=chat_path,
    )
    _registry.register(openai_provider, set_as_default=True)
    
    logger.info(f"提供商注册表初始化完成，已注册: {_registry.list_providers()}")
    return _registry


def get_registry() -> ProviderRegistry:
    """获取全局注册表"""
    if _registry is None:
        raise RuntimeError("提供商注册表未初始化，请先调用 init_registry()")
    return _registry


def get_provider(model: str) -> BaseProvider:
    """
    根据模型获取提供商的便捷函数。
    
    Args:
        model: 模型 ID
        
    Returns:
        支持该模型的提供商
    """
    return get_registry().get_provider(model)
