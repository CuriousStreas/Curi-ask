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

## 配置说明（backend/.env）

- **AI_API_BASE_URL**（必填）：聚合 API 基础地址，如 `https://poloapi.top`。无默认值。
- **AI_API_KEY**（必填）：鉴权密钥，放在请求头 `Authorization: Bearer <key>`。
- **AI_CHAT_PATH**（可选）：聊天接口路径，默认 `/v1/chat/completions`。最终请求地址 = BASE_URL + AI_CHAT_PATH。若平台需单独追加 `/v1` 或 `/v1/chat/completions`，可在此配置。
- **AI_MODELS**（可选）：逗号分隔的模型 id，如 `model-a,model-b`。不填则前端模型下拉为空，需在 .env 中配置你实际可用的模型。
- **PORT**：后端端口，默认 3001。

不同模型的请求方式可参考聚合平台文档（如 Apifox）；Claude 等若支持原生接口，可改 `backend/chat_service.py` 中 URL 与请求体。
