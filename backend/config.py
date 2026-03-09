import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 3001))
AI_BASE_URL = (os.environ.get("AI_API_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODELS_STR = os.environ.get(
    "AI_MODELS",
    "gpt-4o,gpt-4o-mini,gpt-3.5-turbo,claude-3-5-sonnet,claude-3-haiku",
)
MODELS = [{"id": m, "name": m} for m in AI_MODELS_STR.split(",")]
