# Curi Ask

前后端分离的 AI 问答 Web：**Vue 3** 前端提供聊天界面与模型选择，**Flask** 后端统一转发到你的聚合 API。

## ✨ 功能特性

- 🚀 **流式输出**：实时显示 AI 回复，打字机效果
- 📝 **Markdown 渲染**：支持标题、列表、表格、引用等富文本格式
- 🎨 **代码高亮**：自动识别编程语言并语法高亮
- 🗑️ **对话管理**：支持新建、切换、删除对话
- ⏹️ **停止生成**：随时中断 AI 回复
- 🌓 **深色/浅色主题**：自动保存主题偏好
- 📱 **响应式设计**：适配桌面和移动端
- 📊 **完善日志**：后端详细记录请求和错误
- 🔌 **模块化架构**：提供商系统，易于扩展新模型

## 🤖 支持的模型

### Gemini 系列（内置）

| 模型 ID                          | 名称                | 说明               |
| -------------------------------- | ------------------- | ------------------ |
| `gemini-pro-latest`              | Gemini Pro Latest   | 最新版 Pro         |
| `gemini-pro-latest-thinking-exp` | Gemini Pro Thinking | 带思考链（实验性） |
| `gemini-flash-latest`            | Gemini Flash Latest | 最新版 Flash       |

### 其他兼容模型

通过 OpenAI 兼容接口，还支持：

- GPT 系列 (`gpt-4`, `gpt-3.5-turbo` 等)
- Claude 系列 (`claude-3-opus`, `claude-3-sonnet` 等)
- DeepSeek、通义千问、GLM 等国产模型

## 结构

```
backend/
├── app.py              # Flask 主应用
├── chat_service.py     # 聊天服务（统一接口）
├── config.py           # 配置管理
├── providers/          # 模型提供商模块
│   ├── __init__.py
│   ├── base.py         # 提供商基类
│   ├── openai_compatible.py  # OpenAI 兼容接口
│   ├── gemini.py       # Gemini 专用提供商
│   └── registry.py     # 提供商注册表
└── requirements.txt

frontend/
├── src/
│   ├── App.vue         # 主组件（聊天界面）
│   ├── index.css       # 全局样式
│   └── main.js
├── package.json
└── vite.config.js
```

- **backend**（Python Flask）：模块化提供商架构，支持 `GET /api/models`、`POST /api/chat`（非流式）、`POST /api/chat/stream`（流式 SSE）。
- **frontend**（Vue 3 + Vite + marked + highlight.js）：单页聊天 UI + Markdown 渲染 + 代码高亮。

架构与 React+Express 的对照说明见 [docs/架构类比说明.md](docs/架构类比说明.md)。

## 运行

### 1. 后端（Flask）

```bash
cd backend
cp .env.example .env
# 编辑 .env：填写 AI_API_BASE_URL、AI_API_KEY（你的聚合 API 地址和密钥）
pip install -r requirements.txt
python app.py
```

默认端口：`3001`。

### 2. 前端（Vue）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：`http://localhost:5173`。开发时前端的 `/api` 会代理到 `http://localhost:3001`。

### 3. 生产

- 后端：用 gunicorn 等部署 Flask（如 `gunicorn -w 1 -b 0.0.0.0:3001 "app:app"`）。
- 前端：`npm run build`，将 `dist` 部署到任意静态服务；需让前端请求指向实际后端地址（如环境变量或构建时替换 `API_BASE`）。

## 配置说明（backend/.env）

- **AI_API_BASE_URL**（必填）：聚合 API 基础地址，如 `https://poloapi.top`。无默认值。
- **AI_API_KEY**（必填）：鉴权密钥，放在请求头 `Authorization: Bearer <key>`。
- **AI_CHAT_PATH**（可选）：聊天接口路径，默认 `/v1/chat/completions`。最终请求地址 = BASE_URL + AI_CHAT_PATH。若平台需单独追加 `/v1` 或 `/v1/chat/completions`，可在此配置。
- **AI_MODELS**（可选）：逗号分隔的模型 id，如 `model-a,model-b`。不填则前端模型下拉为空，需在 .env 中配置你实际可用的模型。
- **PORT**：后端端口，默认 3001。

不同模型的请求方式可参考聚合平台文档（如 Apifox）；Claude 等若支持原生接口，可改 `backend/chat_service.py` 中 URL 与请求体。

## 🔧 扩展新模型提供商

系统采用模块化的提供商架构，添加新模型非常简单：

### 1. 创建提供商类

在 `backend/providers/` 目录下创建新文件，如 `my_provider.py`：

```python
from .openai_compatible import OpenAICompatibleProvider

class MyProvider(OpenAICompatibleProvider):
    name = "my_provider"
    supported_models = ["my-model-"]  # 模型前缀

    def __init__(self, base_url: str, api_key: str = None, **kwargs):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            chat_path="/v1/chat/completions",  # 自定义路径
            **kwargs
        )
```

### 2. 注册提供商

在 `backend/providers/registry.py` 的 `init_registry` 函数中添加：

```python
from .my_provider import MyProvider

my_provider = MyProvider(base_url=base_url, api_key=api_key)
_registry.register(my_provider)
```

### 3. 添加模型列表（可选）

在提供商文件中定义预设模型：

```python
MY_MODELS = [
    {"id": "my-model-v1", "name": "My Model V1", "description": "描述"},
]
```

然后在 `app.py` 的 `get_all_models()` 中合并。
