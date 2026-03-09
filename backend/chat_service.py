"""
调用 AI 接口（OpenAI 兼容格式）。
若你的聚合 API 格式不同，只需改本文件中的 URL 与请求体。
"""
import requests
from config import AI_BASE_URL, AI_API_KEY


def chat_completion(model: str, messages: list) -> dict:
    url = f"{AI_BASE_URL}/chat/completions"
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
