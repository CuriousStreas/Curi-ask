# Curi Ask

前后端分离的 AI 问答 Web：**Vue 3** 前端提供聊天界面与模型选择，**Flask** 后端统一转发到你的聚合 API。

## 结构

- **backend**（Python Flask）：提供 `GET /api/models`、`POST /api/chat`，按所选模型调用 AI 接口。
- **frontend**（Vue 3 + Vite）：单页聊天 UI + 模型下拉框，开发时通过 Vite 代理请求后端。

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

## 配置说明

- **AI_API_BASE_URL**：聚合 API 的基础 URL（如 `https://api.openai.com/v1`），需兼容 OpenAI 的 `POST /chat/completions` 格式。
- **AI_API_KEY**：若聚合站需要鉴权，填密钥。
- **AI_MODELS**：可选，逗号分隔的模型 id，如 `gpt-4o,gpt-4o-mini`。不填则使用默认列表。

若你的聚合 API 不是 OpenAI 兼容格式，只需修改 `backend/chat_service.py` 中的 URL 与请求体。
