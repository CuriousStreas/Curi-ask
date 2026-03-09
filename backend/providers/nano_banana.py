"""
Nano Banana 图片生成提供商。
通过 Google 原生 API 格式调用图片生成模型。

支持的模型:
- gemini-3.1-flash-image-preview:image: 快速图片生成 (使用 :image:generateContent)
- gemini-3-pro-image-preview:image: 高质量图片生成 (使用 :image:generateContent)
- gemini-3-pro-image-preview: 高质量图片生成 (使用 :generateContent)
"""
import json
import base64
import logging
import requests
from typing import Generator, List, Dict, Any, Optional

from .base import BaseProvider

logger = logging.getLogger(__name__)


class NanoBananaProvider(BaseProvider):
    """
    Nano Banana 图片生成提供商。
    使用 Google 原生 API 格式，支持文本生成图片和图片编辑。
    """
    
    name = "nano_banana"
    
    # 支持的模型（严格按照 API 要求的名称）
    supported_models = [
        "gemini-3.1-flash-image-preview:image",   # 快速图片生成
        "gemini-3-pro-image-preview:image",       # 高质量图片生成 (image 模式)
        "gemini-3-pro-image-preview",             # 高质量图片生成 (标准模式)
    ]
    
    # 模型到 API 路径的映射（严格按照用户提供的端点）
    MODEL_ENDPOINTS = {
        "gemini-3.1-flash-image-preview:image": "/v1beta/models/gemini-3.1-flash-image-preview:image:generateContent",
        "gemini-3-pro-image-preview:image": "/v1beta/models/gemini-3-pro-image-preview:image:generateContent",
        "gemini-3-pro-image-preview": "/v1beta/models/gemini-3-pro-image-preview:generateContent",
    }
    
    # 默认模型
    DEFAULT_MODEL = "gemini-3.1-flash-image-preview:image"
    
    def supports_model(self, model: str) -> bool:
        """
        精确匹配支持的模型（覆写基类方法）。
        Nano Banana 模型需要精确匹配，不使用前缀匹配。
        """
        return model in self.supported_models
    
    def __init__(self, base_url: str, api_key: str = None, **kwargs):
        """
        初始化 Nano Banana 提供商。
        
        Args:
            base_url: API 基础地址
            api_key: API 密钥
            **kwargs: 其他配置
        """
        super().__init__(base_url, api_key, **kwargs)
        self.timeout = kwargs.get('timeout', 120)
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = self.api_key  # Google 原生格式，直接用 key
        return headers
    
    def _get_endpoint(self, model: str) -> str:
        """获取模型对应的 API 端点"""
        return self.MODEL_ENDPOINTS.get(model, self.MODEL_ENDPOINTS[self.DEFAULT_MODEL])
    
    def _build_url(self, model: str) -> str:
        """构建请求 URL"""
        endpoint = self._get_endpoint(model)
        return f"{self.base_url}{endpoint}"
    
    def _build_payload_single(
        self,
        prompt: str,
        images: Optional[List[Dict[str, str]]] = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1024x1024",
    ) -> dict:
        """
        构建单轮请求体（向后兼容）。
        
        Args:
            prompt: 文本提示
            images: 图片列表，每个元素包含 mime_type 和 data (base64)
            aspect_ratio: 宽高比，如 "1:1", "16:9", "9:16"
            image_size: 图片尺寸，如 "1024x1024", "4K"
        """
        parts = [{"text": prompt}]
        
        # 添加图片（如果有）
        if images:
            for img in images:
                parts.append({
                    "inline_data": {
                        "mime_type": img.get("mime_type", "image/jpeg"),
                        "data": img.get("data", "")
                    }
                })
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        # Nano Banana Pro 支持更多配置
        if aspect_ratio or image_size:
            payload["generationConfig"]["imageConfig"] = {}
            if aspect_ratio:
                payload["generationConfig"]["imageConfig"]["aspectRatio"] = aspect_ratio
            if image_size:
                payload["generationConfig"]["imageConfig"]["imageSize"] = image_size
        
        return payload
    
    def _build_payload_multi_turn(
        self,
        messages: List[Dict[str, Any]],
        current_images: Optional[List[Dict[str, str]]] = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1024x1024",
    ) -> dict:
        """
        构建多轮对话请求体，支持图片迭代修改。
        
        Args:
            messages: 完整消息历史，包含 role, content, images 字段
            current_images: 当前轮用户上传的图片
            aspect_ratio: 宽高比
            image_size: 图片尺寸
        """
        contents = []
        
        for msg in messages:
            role = msg.get("role", "user")
            # Gemini API 使用 "user" 和 "model"
            api_role = "model" if role == "assistant" else "user"
            
            parts = []
            
            # 添加文本
            content = msg.get("content", "")
            if content:
                parts.append({"text": content})
            
            # 添加消息中的图片（历史图片，包括 AI 生成的）
            msg_images = msg.get("images", [])
            for img in msg_images:
                parts.append({
                    "inline_data": {
                        "mime_type": img.get("mime_type", "image/png"),
                        "data": img.get("data", "")
                    }
                })
            
            if parts:
                contents.append({
                    "role": api_role,
                    "parts": parts
                })
        
        # 如果当前轮有用户上传的图片，添加到最后一条 user 消息
        if current_images and contents:
            # 找到最后一条 user 消息
            for i in range(len(contents) - 1, -1, -1):
                if contents[i]["role"] == "user":
                    for img in current_images:
                        contents[i]["parts"].append({
                            "inline_data": {
                                "mime_type": img.get("mime_type", "image/jpeg"),
                                "data": img.get("data", "")
                            }
                        })
                    break
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        # 图片配置
        if aspect_ratio or image_size:
            payload["generationConfig"]["imageConfig"] = {}
            if aspect_ratio:
                payload["generationConfig"]["imageConfig"]["aspectRatio"] = aspect_ratio
            if image_size:
                payload["generationConfig"]["imageConfig"]["imageSize"] = image_size
        
        return payload
    
    def generate_image(
        self,
        model: str,
        prompt: str,
        images: Optional[List[Dict[str, str]]] = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1024x1024",
    ) -> Dict[str, Any]:
        """
        生成图片（单轮，非流式）。向后兼容的简单接口。
        
        Args:
            model: 模型 ID
            prompt: 文本提示
            images: 输入图片列表（用于图片编辑）
            aspect_ratio: 宽高比
            image_size: 图片尺寸
            
        Returns:
            包含生成结果的字典，可能包含 text 和 images
        """
        url = self._build_url(model)
        headers = self._build_headers()
        payload = self._build_payload_single(prompt, images, aspect_ratio, image_size)
        
        logger.info(f"[NanoBanana] 单轮图片生成 - 模型: {model}, 提示长度: {len(prompt)}, 输入图片数: {len(images) if images else 0}")
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise RuntimeError("图片生成请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise RuntimeError(f"网络请求失败: {str(e)}")
        
        if not resp.ok:
            err = self._extract_error(resp)
            logger.error(f"API 错误 {resp.status_code}: {err}")
            raise RuntimeError(f"图片生成失败 ({resp.status_code}): {err}")
        
        return self._parse_response(resp.json(), model)
    
    def _parse_response(self, data: dict, model: str) -> Dict[str, Any]:
        """解析 API 响应"""
        result = {
            "model": model,
            "text": None,
            "images": []
        }
        
        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("API 响应中没有 candidates")
            return result
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        
        for part in parts:
            # 文本部分
            if "text" in part:
                result["text"] = part["text"]
            # 图片部分
            elif "inlineData" in part:
                inline_data = part["inlineData"]
                result["images"].append({
                    "mime_type": inline_data.get("mimeType", "image/png"),
                    "data": inline_data.get("data", "")
                })
        
        logger.info(f"[NanoBanana] 响应解析完成 - 文本: {bool(result['text'])}, 图片数: {len(result['images'])}")
        return result
    
    def _extract_error(self, resp: requests.Response) -> str:
        """从响应中提取错误信息"""
        err = resp.text
        try:
            data = resp.json()
            if "error" in data:
                error_obj = data["error"]
                if isinstance(error_obj, dict):
                    err = error_obj.get("message", str(error_obj))
                else:
                    err = str(error_obj)
        except Exception:
            pass
        return err
    
    def _generate_multi_turn(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        current_images: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        多轮对话图片生成，支持图片迭代修改。
        
        Args:
            model: 模型 ID
            messages: 完整消息历史
            current_images: 当前轮用户上传的图片
        """
        url = self._build_url(model)
        headers = self._build_headers()
        payload = self._build_payload_multi_turn(messages, current_images)
        
        # 计算历史图片数
        history_images = sum(len(m.get("images", [])) for m in messages)
        logger.info(f"[NanoBanana] 多轮对话 - 模型: {model}, 消息数: {len(messages)}, 历史图片: {history_images}, 当前图片: {len(current_images) if current_images else 0}")
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise RuntimeError("图片生成请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise RuntimeError(f"网络请求失败: {str(e)}")
        
        if not resp.ok:
            err = self._extract_error(resp)
            logger.error(f"API 错误 {resp.status_code}: {err}")
            raise RuntimeError(f"图片生成失败 ({resp.status_code}): {err}")
        
        return self._parse_response(resp.json(), model)
    
    # 实现基类的抽象方法
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        images: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        非流式对话，支持多轮图片修改。
        
        Args:
            model: 模型 ID
            messages: 消息列表，每条消息可包含 images 字段
            images: 当前轮用户上传的图片
        """
        if not messages:
            raise RuntimeError("没有提供消息内容")
        
        # 使用多轮对话模式
        return self._generate_multi_turn(model, messages, current_images=images)
    
    def chat_completion_stream(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        images: Optional[List[Dict[str, str]]] = None
    ) -> Generator[str, None, None]:
        """
        流式对话（图片生成不支持真正的流式，返回完整结果）。
        支持多轮图片修改。
        
        Args:
            model: 模型 ID
            messages: 消息列表，每条消息可包含 images 字段
            images: 当前轮用户上传的图片
        """
        try:
            result = self.chat_completion(model, messages, images=images)
            
            # 先返回文本
            if result.get("text"):
                yield self._format_sse({
                    "content": result["text"],
                    "model": model,
                    "done": False
                })
            
            # 返回图片
            for img in result.get("images", []):
                yield self._format_sse({
                    "content": "",
                    "model": model,
                    "image": {
                        "mime_type": img["mime_type"],
                        "data": img["data"]
                    },
                    "done": False
                })
            
            # 完成
            yield self._format_sse({
                "content": "",
                "model": model,
                "done": True
            })
        except Exception as e:
            yield self._format_error_sse(str(e))


# 预定义的 Nano Banana 模型列表（严格按照 API 要求的名称）
NANO_BANANA_MODELS = [
    {
        "id": "gemini-3.1-flash-image-preview:image",
        "name": "Nano Banana Flash",
        "description": "快速图片生成，适合高频率使用",
        "type": "image",
    },
    {
        "id": "gemini-3-pro-image-preview:image",
        "name": "Nano Banana Pro (Image)",
        "description": "高质量图片生成 (image 模式)，支持复杂指令",
        "type": "image",
    },
    {
        "id": "gemini-3-pro-image-preview",
        "name": "Nano Banana Pro",
        "description": "高质量图片生成 (标准模式)，支持高保真文本渲染",
        "type": "image",
    },
]
