"""
OpenAI 兼容接口提供商。
支持所有使用 OpenAI API 格式的服务，包括:
- OpenAI 官方 API
- Gemini (通过聚合 API)
- Claude (通过聚合 API)
- 其他兼容服务
"""
import json
import logging
import requests
from typing import Generator, List, Dict, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseProvider):
    """
    OpenAI 兼容接口提供商。
    适用于所有使用 /v1/chat/completions 格式的 API。
    """
    
    name = "openai_compatible"
    
    # 默认支持的模型前缀
    supported_models = [
        "gpt-",           # OpenAI GPT 系列
        "gemini-",        # Google Gemini 系列
        "claude-",        # Anthropic Claude 系列
        "deepseek-",      # DeepSeek 系列
        "qwen-",          # 阿里通义千问
        "glm-",           # 智谱 GLM
        "moonshot-",      # Moonshot
        "yi-",            # 零一万物
    ]
    
    def __init__(self, base_url: str, api_key: str = None, chat_path: str = "/v1/chat/completions", **kwargs):
        """
        初始化 OpenAI 兼容提供商。
        
        Args:
            base_url: API 基础地址
            api_key: API 密钥
            chat_path: 聊天接口路径，默认 /v1/chat/completions
            **kwargs: 其他配置
        """
        super().__init__(base_url, api_key, **kwargs)
        self.chat_path = chat_path if chat_path.startswith("/") else f"/{chat_path}"
        self.timeout = kwargs.get('timeout', 120)
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _build_url(self) -> str:
        """构建请求 URL"""
        return f"{self.base_url}{self.chat_path}"
    
    def _build_payload(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> dict:
        """构建请求体"""
        return {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": stream,
        }
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """非流式对话"""
        url = self._build_url()
        headers = self._build_headers()
        payload = self._build_payload(model, messages, stream=False)
        
        logger.info(f"[{self.name}] 非流式请求 - 模型: {model}, 消息数: {len(messages)}")
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise RuntimeError("AI API 请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise RuntimeError(f"网络请求失败: {str(e)}")
        
        if not resp.ok:
            err = self._extract_error(resp)
            logger.error(f"AI API 错误 {resp.status_code}: {err}")
            raise RuntimeError(f"AI API 错误 {resp.status_code}: {err}")
        
        data = resp.json()
        choice = (data.get("choices") or [None])[0]
        if not choice:
            raise RuntimeError("AI 返回格式异常，无 choices")
        
        msg = choice.get("message") or {}
        response_model = data.get("model") or model
        
        logger.info(f"[{self.name}] 响应成功 - 模型: {response_model}")
        
        return {
            "content": msg.get("content", ""),
            "role": "assistant",
            "model": response_model,
        }
    
    def chat_completion_stream(self, model: str, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """流式对话"""
        url = self._build_url()
        headers = self._build_headers()
        payload = self._build_payload(model, messages, stream=True)
        
        # 调试日志（隐藏敏感信息）
        auth_header = headers.get("Authorization", "")
        auth_preview = f"{auth_header[:20]}...{auth_header[-4:]}" if len(auth_header) > 24 else auth_header
        logger.info(f"[{self.name}] 流式请求 - URL: {url}, 模型: {model}, 消息数: {len(messages)}, Auth: {auth_preview}")
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout, stream=True)
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            yield self._format_error_sse("AI API 请求超时，请稍后重试")
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            yield self._format_error_sse(f"网络请求失败: {str(e)}")
            return
        
        if not resp.ok:
            err = self._extract_error(resp)
            logger.error(f"AI API 错误 {resp.status_code}: {err}")
            yield self._format_error_sse(f"AI API 错误 {resp.status_code}: {err}")
            return
        
        response_model = model
        full_content = ""
        
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choice = (data.get("choices") or [{}])[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_content += content
                            yield self._format_sse({
                                "content": content,
                                "model": response_model,
                                "done": False
                            })
                        
                        # 获取模型名称
                        if data.get("model"):
                            response_model = data.get("model")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"流式读取异常: {e}")
            yield self._format_error_sse(f"流式读取失败: {str(e)}")
            return
        
        logger.info(f"[{self.name}] 流式响应完成 - 模型: {response_model}, 总长度: {len(full_content)}")
        yield self._format_sse({"content": "", "model": response_model, "done": True})
    
    def _extract_error(self, resp: requests.Response) -> str:
        """从响应中提取错误信息"""
        err = resp.text
        try:
            data = resp.json()
            err = data.get("error", {}).get("message", data.get("message", err))
        except Exception:
            pass
        return err
