"""
调用聚合 API（OpenAI 兼容格式）。
鉴权：将密钥放在 Header Authorization: Bearer <key>。
请求地址 = AI_API_BASE_URL + AI_CHAT_PATH，可由 .env 单独配置。
"""
import requests
from config import AI_API_BASE_URL, AI_API_KEY, AI_CHAT_PATH


def chat_completion(model: str, messages: list) -> dict:
    if not AI_API_BASE_URL:
        raise RuntimeError("未配置 AI_API_BASE_URL，请在 backend/.env 中设置")
    path = AI_CHAT_PATH if AI_CHAT_PATH.startswith("/") else f"/{AI_CHAT_PATH}"
    url = f"{AI_API_BASE_URL.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"
    payload = {
        "model": model,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "stream": False,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        err = resp.text
        try:
            data = resp.json()
            err = data.get("error", {}).get("message", data.get("message", err))
        except Exception:
            pass
        raise RuntimeError(f"AI API 错误 {resp.status_code}: {err}")
    data = resp.json()
    choice = (data.get("choices") or [None])[0]
    if not choice:
        raise RuntimeError("AI 返回格式异常，无 choices")
    msg = choice.get("message") or {}
    return {
        "content": msg.get("content", ""),
        "role": "assistant",
        "model": data.get("model") or model,
    }
