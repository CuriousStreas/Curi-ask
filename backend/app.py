from flask import Flask, request, jsonify
from flask_cors import CORS

from config import PORT, MODELS
from chat_service import chat_completion

app = Flask(__name__)
CORS(app)


@app.route("/api/models", methods=["GET"])
def api_models():
    return jsonify(models=MODELS)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        body = request.get_json(silent=True) or {}
        model = body.get("model")
        messages = body.get("messages")
        if not model or not isinstance(messages, list) or len(messages) == 0:
            return jsonify(error="请提供 model 和 messages"), 400
        result = chat_completion(model, messages)
        return jsonify(result)
    except RuntimeError as e:
        return jsonify(error=str(e)), 500
    except Exception as e:
        return jsonify(error="对话请求失败"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
