"""
塔菲酱（L50 Chat）提供商。
内网限定的 AI 助手，通过 L50 API 调用。

支持的模型:
- taffy: 塔菲酱（内网限定）
"""
import json
import logging
import requests
from typing import Generator, List, Dict, Any, Optional

from .base import BaseProvider

logger = logging.getLogger(__name__)


class TaffyProvider(BaseProvider):
    """
    塔菲酱提供商。
    使用 L50 Chat API，支持流式对话。
    """
    
    name = "taffy"
    
    # 支持的模型
    supported_models = [
        "taffy",           # 塔菲酱（标准模式）
        "taffy-think",     # 塔菲酱（显示思考过程）
    ]
    
    # L50 API 地址
    DEFAULT_API_URL = "https://links-l50-pro.apps-sl.danlu.netease.com/api/v1/mcp_rag"
    
    def supports_model(self, model: str) -> bool:
        """精确匹配支持的模型"""
        return model in self.supported_models
    
    def __init__(self, base_url: str = None, api_key: str = None, **kwargs):
        """
        初始化塔菲酱提供商。
        
        Args:
            base_url: API 基础地址（可选，默认使用内网地址）
            api_key: API 密钥（L50 不需要）
            **kwargs: 其他配置
        """
        # L50 使用固定的内网地址
        super().__init__(base_url or self.DEFAULT_API_URL, api_key, **kwargs)
        self.timeout = kwargs.get('timeout', 120)
        self.api_url = self.DEFAULT_API_URL
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/json"
        }
    
    def _build_payload(
        self,
        query: str,
        session_id: str,
        show_think: bool = False,
        image_list: Optional[List[str]] = None,
        stream: bool = True
    ) -> dict:
        """
        构建请求体。
        
        Args:
            query: 用户输入
            session_id: 会话ID
            show_think: 是否显示思考过程
            image_list: 图片列表
            stream: 是否流式
        """
        return {
            "query": query,
            "stream": stream,
            "task_type": "l50",
            "session_id": session_id,
            "show_think_flag": show_think,
            "short_answer_flag": True,
            "image_list": image_list or []
        }
    
    def _generate_session_id(self, messages: List[Dict]) -> str:
        """
        根据消息历史生成或获取会话ID。
        使用消息列表的哈希来保持同一对话的会话ID一致。
        """
        # 简单的会话ID生成：使用前几条消息的内容哈希
        if not messages:
            import uuid
            return f"taffy_{uuid.uuid4().hex[:8]}"
        
        # 使用第一条消息的内容作为会话标识
        first_msg = messages[0].get("content", "")[:50]
        import hashlib
        hash_str = hashlib.md5(first_msg.encode()).hexdigest()[:8]
        return f"taffy_{hash_str}"
    
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        images: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        非流式对话（同步收集完整响应）。
        
        Args:
            model: 模型 ID
            messages: 消息列表
            images: 图片列表（暂不支持）
        """
        if not messages:
            raise RuntimeError("没有提供消息内容")
        
        # 获取最后一条用户消息
        last_message = messages[-1]
        query = last_message.get("content", "")
        
        # 生成会话ID
        session_id = self._generate_session_id(messages)
        
        # 是否显示思考过程
        show_think = model == "taffy-think"
        
        # 构建请求
        payload = self._build_payload(query, session_id, show_think, stream=True)
        headers = self._build_headers()
        
        logger.info(f"[Taffy] 请求 - 会话: {session_id}, 查询长度: {len(query)}")
        
        try:
            resp = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout,
                stream=True
            )
            resp.raise_for_status()
            
            # 收集完整响应
            result = {
                "model": model,
                "text": "",
                "think": ""
            }
            
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                if line.startswith("think:"):
                    content = line[len("think:"):]
                    result["think"] += content
                elif line.startswith("data:"):
                    content = line[len("data:"):]
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            chunk = data.get('content', '')
                            if chunk:
                                result["text"] += chunk
                    except json.JSONDecodeError:
                        if content != "[DONE]":
                            result["text"] += content
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {self.api_url}")
            raise RuntimeError("塔菲酱请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise RuntimeError(f"网络请求失败: {str(e)}")
    
    def chat_completion_stream(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        images: Optional[List[Dict[str, str]]] = None
    ) -> Generator[str, None, None]:
        """
        流式对话。
        塔菲酱不需要上下文记忆，只发送当前消息。
        
        Args:
            model: 模型 ID
            messages: 消息列表（只使用最后一条）
            images: 图片列表（暂不支持）
        """
        if not messages:
            yield self._format_error_sse("没有提供消息内容")
            return
        
        # 只使用最后一条用户消息，不发送历史上下文
        last_message = messages[-1]
        query = last_message.get("content", "")
        
        # 每次生成新的会话ID（不保持上下文）
        import uuid
        session_id = f"taffy_{uuid.uuid4().hex[:8]}"
        
        # 是否显示思考过程
        show_think = model == "taffy-think"
        
        # 构建请求
        payload = self._build_payload(query, session_id, show_think, stream=True)
        headers = self._build_headers()
        
        logger.info(f"[Taffy] 流式请求 - 会话: {session_id}, 查询长度: {len(query)}")
        
        try:
            resp = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout,
                stream=True
            )
            resp.raise_for_status()
            
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                if line.startswith("think:"):
                    # 思考过程，用特殊格式包装
                    if show_think:
                        content = line[len("think:"):]
                        yield self._format_sse({
                            "content": f"💭 {content}",  # 用表情标记思考内容
                            "model": model,
                            "type": "think",
                            "done": False
                        })
                
                elif line.startswith("data:"):
                    content = line[len("data:"):]
                    
                    if content == "[DONE]":
                        # 流结束
                        yield self._format_sse({
                            "content": "",
                            "model": model,
                            "done": True
                        })
                        return
                    
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            chunk = data.get('content', '')
                            if chunk:
                                yield self._format_sse({
                                    "content": chunk,
                                    "model": model,
                                    "done": False
                                })
                    except json.JSONDecodeError:
                        # 非JSON内容，直接输出
                        yield self._format_sse({
                            "content": content,
                            "model": model,
                            "done": False
                        })
            
            # 确保发送结束标记
            yield self._format_sse({
                "content": "",
                "model": model,
                "done": True
            })
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {self.api_url}")
            yield self._format_error_sse("塔菲酱请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            yield self._format_error_sse(f"网络请求失败: {str(e)}")
        except Exception as e:
            logger.exception(f"未知异常: {e}")
            yield self._format_error_sse(str(e))


# 预定义的塔菲酱模型列表
TAFFY_MODELS = [
    {
        "id": "taffy",
        "name": "� 塔菲酱（内网限定）",
        "description": "内网 AI 助手，基于 L50 Chat API",
        "type": "chat",
    },
    {
        "id": "taffy-think",
        "name": "� 塔菲酱（思考模式）",
        "description": "显示思考过程的塔菲酱",
        "type": "chat",
    },
]
