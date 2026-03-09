import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 3001))

# 聚合 API：仅使用你配置的 URL + 令牌，无默认值
AI_API_BASE_URL = (os.environ.get("AI_API_BASE_URL") or "").strip().rstrip("/")
AI_API_KEY = (os.environ.get("AI_API_KEY") or "").strip()

# 聊天接口路径：部分平台需追加 /v1 或 /v1/chat/completions，在此单独配置
# 最终请求地址 = AI_API_BASE_URL + AI_CHAT_PATH，例如 https://poloapi.top/v1/chat/completions
AI_CHAT_PATH = (os.environ.get("AI_CHAT_PATH") or "/v1/chat/completions").strip()
if not AI_CHAT_PATH.startswith("/"):
    AI_CHAT_PATH = "/" + AI_CHAT_PATH

# 模型列表：仅从环境变量读取，不写死。未配置时为空，前端下拉为空
AI_MODELS_STR = (os.environ.get("AI_MODELS") or "").strip()
MODELS = [{"id": m, "name": m} for m in AI_MODELS_STR.split(",") if m]
