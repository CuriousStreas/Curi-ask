<template>
  <div class="app">
    <!-- 侧边栏：左上角名字 + 对话列表（Gemini 风格） -->
    <aside class="sidebar" :class="{ 'sidebar--open': sidebarOpen }">
      <div class="sidebar-head">
        <h1 class="logo">Curi Ask</h1>
        <button
          v-if="isMobile"
          type="button"
          class="icon-btn sidebar-close"
          aria-label="关闭侧边栏"
          @click="sidebarOpen = false"
        >
          ×
        </button>
      </div>
      <button type="button" class="new-chat-btn" @click="startNewChat">
        + 新对话
      </button>
      <div class="conversation-list">
        <button
          v-for="c in conversations"
          :key="c.id"
          type="button"
          :class="['conversation-item', { 'conversation-item--active': currentId === c.id }]"
          @click="selectConversation(c.id)"
        >
          <span class="conversation-title">{{ c.title }}</span>
        </button>
        <p v-if="conversations.length === 0" class="conversation-empty">暂无对话</p>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-wrap">
      <header class="header">
        <button
          v-if="isMobile"
          type="button"
          class="icon-btn menu-btn"
          aria-label="打开侧边栏"
          @click="sidebarOpen = true"
        >
          ☰
        </button>
        <div class="header-spacer"></div>
        <div class="header-right">
          <select
            id="model"
            v-model="model"
            :disabled="loading"
            class="model-select"
            aria-label="选择模型"
          >
            <option v-if="models.length === 0" value="" disabled>请配置后端 AI_MODELS</option>
            <option v-for="m in models" :key="m.id" :value="m.id">
              {{ m.name || m.id }}
            </option>
          </select>
          <button
            type="button"
            class="icon-btn"
            :title="theme === 'dark' ? '浅色模式' : '深色模式'"
            @click="toggleTheme"
            aria-label="切换主题"
          >
            <span v-if="theme === 'dark'" class="icon">☀️</span>
            <span v-else class="icon">🌙</span>
          </button>
        </div>
      </header>

      <main class="main" ref="listRef">
        <div class="content">
          <template v-if="messages.length === 0">
            <div class="empty">
              <p class="empty-title">开始对话</p>
              <p class="empty-desc">选择模型后，在下方输入问题。对话会保存在左侧列表中。</p>
            </div>
          </template>
          <template v-else>
            <article
              v-for="(msg, i) in messages"
              :key="i"
              :class="['block', `block--${msg.role}`]"
            >
              <div class="block-label">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
              <div class="block-body">
                <span v-if="msg.model" class="block-model">{{ msg.model }}</span>
                <div class="block-text">{{ msg.content }}</div>
              </div>
            </article>
            <article v-if="loading" class="block block--assistant">
              <div class="block-label">AI</div>
              <div class="block-body">
                <div class="block-text block-text--muted">正在回复…</div>
              </div>
            </article>
          </template>
        </div>
      </main>

      <div v-if="error" class="toast toast--error">
        <span>{{ error }}</span>
        <button type="button" class="toast-close" @click="error = ''">关闭</button>
      </div>

      <div class="footer">
        <form class="input-wrap" @submit.prevent="handleSubmit">
          <textarea
            class="input"
            v-model="input"
            @keydown.enter.exact.prevent="handleSubmit"
            placeholder="输入问题，Enter 发送"
            :disabled="loading"
            rows="1"
            aria-label="输入消息"
          />
          <button
            type="submit"
            class="send-btn"
            :disabled="loading || !input.trim() || !model"
            aria-label="发送"
          >
            发送
          </button>
        </form>
      </div>
    </div>

    <!-- 移动端侧边栏遮罩 -->
    <div
      v-if="isMobile && sidebarOpen"
      class="sidebar-overlay"
      aria-hidden="true"
      @click="sidebarOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';

const THEME_KEY = 'curi-ask-theme';
const CONVERSATIONS_KEY = 'curi-ask-conversations';
const API_BASE = '';

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function getConversationTitle(messages) {
  const first = messages.find((m) => m.role === 'user');
  if (!first || !first.content) return '新对话';
  const t = first.content.trim().replace(/\s+/g, ' ');
  return t.length > 24 ? t.slice(0, 24) + '…' : t;
}

async function getModels() {
  const res = await fetch(`${API_BASE}/api/models`);
  if (!res.ok) throw new Error('获取模型列表失败');
  const data = await res.json();
  return data.models || [];
}

async function sendChat(model, messages) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || '请求失败');
  return data;
}

const models = ref([]);
const model = ref('');
const messages = ref([]);
const input = ref('');
const loading = ref(false);
const error = ref('');
const listRef = ref(null);
const theme = ref('dark');
const conversations = ref([]);
const currentId = ref(null);
const sidebarOpen = ref(false);

const isMobile = ref(false);
function checkMobile() {
  isMobile.value = typeof window !== 'undefined' && window.innerWidth < 768;
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(CONVERSATIONS_KEY);
    if (raw) {
      const list = JSON.parse(raw);
      conversations.value = Array.isArray(list) ? list : [];
    }
  } catch (_) {
    conversations.value = [];
  }
}

function saveConversations() {
  try {
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations.value));
  } catch (_) {}
}

function startNewChat() {
  currentId.value = null;
  messages.value = [];
  if (isMobile.value) sidebarOpen.value = false;
}

function selectConversation(id) {
  const c = conversations.value.find((x) => x.id === id);
  if (!c) return;
  currentId.value = c.id;
  messages.value = c.messages ? [...c.messages] : [];
  if (isMobile.value) sidebarOpen.value = false;
}

function ensureCurrentConversation() {
  if (currentId.value) {
    const c = conversations.value.find((x) => x.id === currentId.value);
    if (c) {
      c.messages = [...messages.value];
      c.title = getConversationTitle(messages.value);
      c.updatedAt = Date.now();
      saveConversations();
      return;
    }
  }
  const id = genId();
  const title = getConversationTitle(messages.value);
  conversations.value.unshift({
    id,
    title,
    messages: [...messages.value],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  });
  currentId.value = id;
  saveConversations();
}

function applyTheme(value) {
  theme.value = value;
  document.documentElement.setAttribute('data-theme', value);
  try {
    localStorage.setItem(THEME_KEY, value);
  } catch (_) {}
}

function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark');
}

onMounted(async () => {
  checkMobile();
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', checkMobile);
  }
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') applyTheme(saved);
    else document.documentElement.setAttribute('data-theme', theme.value);
  } catch (_) {}
  loadConversations();
  try {
    const list = await getModels();
    models.value = list;
    if (list.length && !model.value) model.value = list[0].id;
  } catch (e) {
    error.value = e.message;
  }
});

watch(messages, () => {
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight;
}, { deep: true });

watch(
  messages,
  (val) => {
    if (val.length > 0) ensureCurrentConversation();
  },
  { deep: true }
);

async function handleSubmit() {
  const text = input.value.trim();
  if (!text || !model.value || loading.value) return;
  error.value = '';
  input.value = '';
  const userMsg = { role: 'user', content: text };
  messages.value.push(userMsg);
  loading.value = true;
  try {
    const nextMessages = [...messages.value];
    const result = await sendChat(model.value, nextMessages);
    messages.value.push({
      role: 'assistant',
      content: result.content,
      model: result.model,
    });
  } catch (e) {
    error.value = e.message;
    messages.value.pop();
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  position: relative;
}

/* ----- 侧边栏（Gemini 风格）----- */
.sidebar {
  width: 16rem;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-right: 1px solid var(--border-subtle);
  min-height: 100vh;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  min-height: 3rem;
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  padding: 0;
}

.sidebar-close {
  width: 2rem;
  height: 2rem;
  font-size: 1.25rem;
  line-height: 1;
}

.new-chat-btn {
  margin: 0.5rem 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 0.8125rem;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, border-color 0.15s;
}

.new-chat-btn:hover {
  background: var(--surface-hover);
  border-color: var(--text-tertiary);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.conversation-item {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-item:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.conversation-item--active {
  background: var(--accent-muted);
  color: var(--accent);
}

.conversation-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-empty {
  margin: 1rem 0.75rem 0;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

/* ----- 主区域 ----- */
.main-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* 顶栏：右上角贴边 */
.header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
  min-height: 3rem;
}

.menu-btn {
  position: absolute;
  left: 0.75rem;
  width: 2.25rem;
  height: 2.25rem;
  font-size: 1.125rem;
}

.header-spacer {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.model-select {
  padding: 0.375rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 0.8125rem;
  cursor: pointer;
  min-width: 9rem;
  transition: border-color 0.15s, background 0.15s;
}

.model-select:hover:not(:disabled) {
  background: var(--surface-hover);
}

.model-select:focus {
  outline: none;
  border-color: var(--accent);
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.icon-btn:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.icon {
  font-size: 1.125rem;
  line-height: 1;
}

/* ----- Main ----- */
.main {
  flex: 1;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  padding: 0 1.5rem;
}

.content {
  width: 100%;
  max-width: 45rem;
  padding: 2rem 0 1.5rem;
}

.empty {
  text-align: center;
  padding: 4rem 1rem;
}

.empty-title {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text);
  letter-spacing: -0.01em;
}

.empty-desc {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 28rem;
  margin-left: auto;
  margin-right: auto;
}

.block {
  padding: 1.25rem 0;
  border-bottom: 1px solid var(--border-subtle);
  display: grid;
  grid-template-columns: 5rem 1fr;
  gap: 1rem;
  align-items: start;
}

.block:last-child {
  border-bottom: none;
}

.block--user {
  background: var(--user-bg);
  margin: 0 -1rem;
  padding-left: 1rem;
  padding-right: 1rem;
  margin-bottom: 0;
  border-radius: var(--radius-md);
  border-bottom: none;
  margin-bottom: 1px;
}

.block--assistant {
  background: var(--assistant-bg);
}

.block-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
  padding-top: 0.125rem;
}

.block-body {
  min-width: 0;
}

.block-model {
  display: inline-block;
  font-size: 0.6875rem;
  color: var(--accent);
  font-family: ui-monospace, monospace;
  margin-bottom: 0.25rem;
}

.block-text {
  font-size: 0.9375rem;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text);
}

.block-text--muted {
  color: var(--text-secondary);
}

.toast {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
}

.toast--error {
  background: var(--error-bg);
  color: var(--error);
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 0.8125rem;
  padding: 0.25rem 0;
  flex-shrink: 0;
}

.toast-close:hover {
  text-decoration: underline;
}

.footer {
  flex-shrink: 0;
  padding: 1.25rem 1.5rem 2rem;
  display: flex;
  justify-content: center;
  border-top: 1px solid var(--border-subtle);
}

.input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  width: 100%;
  max-width: 45rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 0.75rem 0.75rem 0.75rem 1rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.input-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-muted);
}

.input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 0.9375rem;
  line-height: 1.5;
  resize: none;
  min-height: 2.25rem;
  max-height: 12rem;
  padding: 0.25rem 0;
}

.input::placeholder {
  color: var(--text-tertiary);
}

.input:focus {
  outline: none;
}

.send-btn {
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 侧边栏遮罩（移动端） */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 8;
}

/* ----- 响应式：移动端侧边栏抽屉 ----- */
@media (max-width: 767px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 10;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }

  .sidebar--open {
    transform: translateX(0);
  }

  .main {
    padding: 0 1rem;
  }

  .content {
    padding: 1.5rem 0 1rem;
  }

  .block {
    grid-template-columns: 3.5rem 1fr;
    gap: 0.75rem;
    padding: 1rem 0;
  }

  .block--user {
    margin-left: -0.5rem;
    margin-right: -0.5rem;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }

  .empty {
    padding: 3rem 0.5rem;
  }

  .footer {
    padding: 1rem;
  }

  .model-select {
    min-width: 7rem;
  }
}
</style>
