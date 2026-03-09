import logging
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from config import PORT, MODELS, AI_API_BASE_URL, AI_API_KEY, AI_CHAT_PATH
from chat_service import chat_completion, chat_completion_stream
from providers import init_registry, GEMINI_MODELS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 初始化提供商注册表
init_registry(
    base_url=AI_API_BASE_URL,
    api_key=AI_API_KEY,
    chat_path=AI_CHAT_PATH,
)

app = Flask(__name__)
CORS(app)


def get_all_models():
    """
    获取所有可用模型列表。
    合并配置文件中的模型和内置的 Gemini 模型。
    """
    # 从环境变量配置的模型
    models = list(MODELS) if MODELS else []
    
    # 添加内置的 Gemini 模型（如果尚未包含）
    existing_ids = {m['id'] for m in models}
    for gm in GEMINI_MODELS:
        if gm['id'] not in existing_ids:
            models.append(gm)
    
    return models


@app.route("/api/models", methods=["GET"])
def api_models():
    models = get_all_models()
    logger.info(f"获取模型列表，共 {len(models)} 个模型")
    return jsonify(models=models)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """非流式对话接口（保留兼容）"""
    try:
        body = request.get_json(silent=True) or {}
        model = body.get("model")
        messages = body.get("messages")
        if not model or not isinstance(messages, list) or len(messages) == 0:
            logger.warning(f"无效请求参数: model={model}, messages_len={len(messages) if isinstance(messages, list) else 'invalid'}")
            return jsonify(error="请提供 model 和 messages"), 400
        
        logger.info(f"[非流式] 收到请求: model={model}, messages_count={len(messages)}")
        result = chat_completion(model, messages)
        return jsonify(result)
    except RuntimeError as e:
        logger.error(f"[非流式] RuntimeError: {str(e)}")
        return jsonify(error=str(e)), 500
    except Exception as e:
        logger.exception(f"[非流式] 未预期异常: {str(e)}")
        return jsonify(error=f"对话请求失败: {str(e)}"), 500


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """流式对话接口（SSE）"""
    try:
        body = request.get_json(silent=True) or {}
        model = body.get("model")
        messages = body.get("messages")
        if not model or not isinstance(messages, list) or len(messages) == 0:
            logger.warning(f"[流式] 无效请求参数: model={model}")
            return jsonify(error="请提供 model 和 messages"), 400
        
        logger.info(f"[流式] 收到请求: model={model}, messages_count={len(messages)}")
        
        def generate():
            try:
                for chunk in chat_completion_stream(model, messages):
                    yield chunk
            except Exception as e:
                logger.exception(f"[流式] 生成异常: {str(e)}")
                import json
                yield f'data: {json.dumps({"error": str(e)})}\n\n'
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',  # 禁用 Nginx 缓冲
            }
        )
    except Exception as e:
        logger.exception(f"[流式] 请求异常: {str(e)}")
        return jsonify(error=f"流式请求失败: {str(e)}"), 500


@app.route("/api/providers", methods=["GET"])
def api_providers():
    """获取已注册的提供商列表"""
    from providers import get_registry
    registry = get_registry()
    return jsonify(providers=registry.list_providers())


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    models = get_all_models()
    return jsonify(status="ok", models_count=len(models))


if __name__ == "__main__":
    models = get_all_models()
    logger.info(f"启动服务器，端口: {PORT}，模型数量: {len(models)}")
    logger.info(f"已加载模型: {[m['id'] for m in models]}")
    app.run(host="0.0.0.0", port=PORT, debug=True, threaded=True)