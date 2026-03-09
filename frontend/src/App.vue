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
        <div
          v-for="c in conversations"
          :key="c.id"
          :class="['conversation-item', { 'conversation-item--active': currentId === c.id }]"
        >
          <button
            type="button"
            class="conversation-title-btn"
            @click="selectConversation(c.id)"
          >
            <span class="conversation-title">{{ c.title }}</span>
          </button>
          <button
            type="button"
            class="conversation-delete-btn"
            @click.stop="deleteConversation(c.id)"
            title="删除对话"
            aria-label="删除对话"
          >
            🗑️
          </button>
        </div>
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
                <!-- 用户消息中的图片预览 -->
                <div v-if="msg.role === 'user' && msg.images && msg.images.length" class="block-images">
                  <img 
                    v-for="(img, idx) in msg.images" 
                    :key="idx"
                    :src="img.preview || `data:${img.mime_type};base64,${img.data}`"
                    class="block-image block-image--user"
                    alt="用户上传的图片"
                  />
                </div>
                <div 
                  v-if="msg.role === 'assistant'"
                  class="block-text markdown-body"
                  v-html="renderMarkdown(msg.content)"
                ></div>
                <div v-else class="block-text">{{ msg.content }}</div>
                <!-- AI 生成的图片 -->
                <div v-if="msg.role === 'assistant' && msg.images && msg.images.length" class="block-images">
                  <div v-for="(img, idx) in msg.images" :key="idx" class="generated-image-wrap">
                    <img 
                      :src="`data:${img.mime_type};base64,${img.data}`"
                      class="block-image block-image--generated"
                      alt="AI 生成的图片"
                      @click="openImagePreview(img)"
                    />
                    <button 
                      type="button" 
                      class="download-btn"
                      @click="downloadImage(img, `generated-${i}-${idx}`)"
                      title="下载图片"
                    >
                      ⬇️
                    </button>
                  </div>
                </div>
              </div>
            </article>
            <article v-if="loading" class="block block--assistant">
              <div class="block-label">AI</div>
              <div class="block-body">
                <span v-if="streamingModel" class="block-model">{{ streamingModel }}</span>
                <div 
                  v-if="streamingContent"
                  class="block-text markdown-body"
                  v-html="renderMarkdown(streamingContent)"
                ></div>
                <div v-else class="block-text block-text--muted">正在回复…</div>
              </div>
            </article>
          </template>
        </div>
      </main>

      <div v-if="error" class="toast toast--error">
        <div class="toast-content">
          <span class="toast-icon">⚠️</span>
          <div class="toast-message">
            <strong>请求失败</strong>
            <p>{{ error }}</p>
          </div>
        </div>
        <button type="button" class="toast-close" @click="error = ''">×</button>
      </div>

      <div 
        class="footer"
        :class="{ 'footer--dragover': isDragOver }"
        @dragover.prevent="handleDragOver"
        @dragleave.prevent="handleDragLeave"
        @drop.prevent="handleDrop"
      >
        <!-- 拖拽提示覆盖层 -->
        <div v-if="isDragOver && isImageModel()" class="drop-overlay">
          <div class="drop-hint">
            <span class="drop-icon">📷</span>
            <span>释放以上传图片</span>
          </div>
        </div>
        
        <!-- 图片预览区域 -->
        <div v-if="uploadedImages.length > 0" class="uploaded-images-preview">
          <div 
            v-for="(img, idx) in uploadedImages" 
            :key="idx" 
            class="uploaded-image-item"
          >
            <img :src="img.preview" :alt="img.name" class="uploaded-image-thumb" />
            <button 
              type="button" 
              class="remove-image-btn"
              @click="removeUploadedImage(idx)"
              title="移除图片"
            >
              ×
            </button>
          </div>
        </div>
        
        <form class="input-wrap" @submit.prevent="handleSubmit">
          <!-- 图片上传按钮（仅图片模型显示） -->
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            multiple
            class="hidden-file-input"
            @change="handleImageUpload"
          />
          <button
            v-if="isImageModel()"
            type="button"
            class="upload-btn"
            @click="triggerFileInput"
            :disabled="loading"
            title="上传图片"
          >
            🖼️
          </button>
          
          <textarea
            ref="textareaRef"
            class="input"
            v-model="input"
            @keydown.enter.exact.prevent="handleSubmit"
            @paste="handlePaste"
            :placeholder="isImageModel() ? '描述你想生成的图片，支持拖入或粘贴图片...' : '输入问题，Enter 发送'"
            :disabled="loading"
            rows="1"
            aria-label="输入消息"
          />
          <button
            v-if="loading"
            type="button"
            class="stop-btn"
            @click="stopStream"
            aria-label="停止生成"
          >
            ⏹️ 停止
          </button>
          <button
            v-else
            type="submit"
            class="send-btn"
            :disabled="!input.trim() || !model"
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

    <!-- 删除确认对话框 -->
    <div v-if="deleteConfirmId" class="modal-overlay" @click="deleteConfirmId = null">
      <div class="modal" @click.stop>
        <h3>确认删除</h3>
        <p>确定要删除这个对话吗？此操作不可撤销。</p>
        <div class="modal-actions">
          <button type="button" class="btn-cancel" @click="deleteConfirmId = null">取消</button>
          <button type="button" class="btn-danger" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';

const THEME_KEY = 'curi-ask-theme';
const CONVERSATIONS_KEY = 'curi-ask-conversations';
const API_BASE = '';

// 图片生成模型列表（支持图片输入的模型）
const IMAGE_MODELS = [
  // Nano Banana 系列 (后端实际模型名)
  'gemini-3.1-flash-image-preview:image',  // Nano Banana Flash
  'gemini-3-pro-image-preview:image',       // Nano Banana Pro (Image)
  'gemini-3-pro-image-preview',             // Nano Banana Pro
  // Gemini 原生多模态模型
  'gemini-2.5-flash-preview-04-17',
  'gemini-2.0-flash',
  'gemini-2.0-flash-lite',
  'gemini-1.5-flash',
  'gemini-1.5-pro',
];

// 配置 marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value;
      } catch (_) {}
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
  gfm: true,
});

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function getConversationTitle(messages) {
  const first = messages.find((m) => m.role === 'user');
  if (!first || !first.content) return '新对话';
  const t = first.content.trim().replace(/\s+/g, ' ');
  return t.length > 24 ? t.slice(0, 24) + '…' : t;
}

function renderMarkdown(content) {
  if (!content) return '';
  try {
    return marked.parse(content);
  } catch (e) {
    console.error('Markdown 渲染失败:', e);
    return content;
  }
}

async function getModels() {
  const res = await fetch(`${API_BASE}/api/models`);
  if (!res.ok) throw new Error('获取模型列表失败');
  const data = await res.json();
  return data.models || [];
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
const deleteConfirmId = ref(null);

// 流式输出相关
const streamingContent = ref('');
const streamingModel = ref('');
const streamingImages = ref([]);  // 流式图片
const abortController = ref(null);

// 图片上传相关
const uploadedImages = ref([]);  // 用户上传的图片
const fileInputRef = ref(null);  // 文件输入框引用
const textareaRef = ref(null);   // 文本框引用
const isDragOver = ref(false);   // 是否正在拖拽

// 判断当前模型是否为图片生成模型
function isImageModel() {
  return IMAGE_MODELS.includes(model.value);
}

// 处理图片上传
function handleImageUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;
  
  for (const file of files) {
    if (!file.type.startsWith('image/')) {
      error.value = '请选择图片文件';
      continue;
    }
    
    if (file.size > 10 * 1024 * 1024) {  // 10MB 限制
      error.value = '图片大小不能超过 10MB';
      continue;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target.result.split(',')[1];  // 去掉 data:image/xxx;base64, 前缀
      uploadedImages.value.push({
        name: file.name,
        mime_type: file.type,
        data: base64,
        preview: e.target.result  // 完整的 data URL 用于预览
      });
    };
    reader.readAsDataURL(file);
  }
  
  // 重置 input 以允许重复选择同一文件
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
}

// 移除上传的图片
function removeUploadedImage(index) {
  uploadedImages.value.splice(index, 1);
}

// 触发文件选择
function triggerFileInput() {
  if (fileInputRef.value) {
    fileInputRef.value.click();
  }
}

// 通用的图片文件处理函数
function processImageFile(file) {
  if (!file.type.startsWith('image/')) {
    error.value = '请选择图片文件';
    return;
  }
  
  if (file.size > 10 * 1024 * 1024) {  // 10MB 限制
    error.value = '图片大小不能超过 10MB';
    return;
  }
  
  const reader = new FileReader();
  reader.onload = (e) => {
    const base64 = e.target.result.split(',')[1];
    uploadedImages.value.push({
      name: file.name || 'pasted-image',
      mime_type: file.type,
      data: base64,
      preview: e.target.result
    });
  };
  reader.readAsDataURL(file);
}

// 处理拖拽进入
function handleDragOver(event) {
  if (!isImageModel()) return;
  
  // 检查是否包含文件
  if (event.dataTransfer && event.dataTransfer.types.includes('Files')) {
    isDragOver.value = true;
  }
}

// 处理拖拽离开
function handleDragLeave(event) {
  // 防止子元素触发 dragleave
  const rect = event.currentTarget.getBoundingClientRect();
  const x = event.clientX;
  const y = event.clientY;
  
  if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
    isDragOver.value = false;
  }
}

// 处理拖拽释放
function handleDrop(event) {
  isDragOver.value = false;
  
  if (!isImageModel()) {
    error.value = '当前模型不支持图片输入，请切换到图片模型';
    return;
  }
  
  const files = event.dataTransfer?.files;
  if (!files || files.length === 0) return;
  
  for (const file of files) {
    processImageFile(file);
  }
}

// 处理粘贴事件
function handlePaste(event) {
  if (!isImageModel()) return;
  
  const items = event.clipboardData?.items;
  if (!items) return;
  
  let hasImage = false;
  
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      hasImage = true;
      const file = item.getAsFile();
      if (file) {
        processImageFile(file);
      }
    }
  }
  
  // 如果粘贴了图片，阻止默认的文本粘贴行为（对于纯图片粘贴）
  // 但如果同时有文本，允许文本粘贴
  if (hasImage && !event.clipboardData.getData('text')) {
    event.preventDefault();
  }
}

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

function deleteConversation(id) {
  deleteConfirmId.value = id;
}

function confirmDelete() {
  const id = deleteConfirmId.value;
  if (!id) return;
  
  const index = conversations.value.findIndex((x) => x.id === id);
  if (index !== -1) {
    conversations.value.splice(index, 1);
    saveConversations();
    
    // 如果删除的是当前对话，清空消息
    if (currentId.value === id) {
      currentId.value = null;
      messages.value = [];
    }
  }
  deleteConfirmId.value = null;
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

function stopStream() {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  // 如果有流式内容，保存到消息中
  if (streamingContent.value) {
    messages.value.push({
      role: 'assistant',
      content: streamingContent.value + '\n\n*[已停止生成]*',
      model: streamingModel.value || model.value,
    });
  }
  streamingContent.value = '';
  streamingModel.value = '';
  loading.value = false;
}

// 下载图片
function downloadImage(img, filename) {
  const link = document.createElement('a');
  link.href = `data:${img.mime_type};base64,${img.data}`;
  link.download = `${filename}.${img.mime_type.split('/')[1] || 'png'}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// 打开图片预览（简单实现：新标签页）
function openImagePreview(img) {
  const dataUrl = `data:${img.mime_type};base64,${img.data}`;
  window.open(dataUrl, '_blank');
}

async function handleSubmit() {
  const text = input.value.trim();
  if (!text || !model.value || loading.value) return;
  error.value = '';
  input.value = '';
  
  // 收集上传的图片
  const imagesToSend = uploadedImages.value.length > 0 
    ? uploadedImages.value.map(img => ({
        mime_type: img.mime_type,
        data: img.data
      }))
    : null;
  
  // 用户消息（包含图片预览）
  const userMsg = { 
    role: 'user', 
    content: text,
    images: uploadedImages.value.length > 0 
      ? uploadedImages.value.map(img => ({
          mime_type: img.mime_type,
          data: img.data,
          preview: img.preview
        }))
      : undefined
  };
  messages.value.push(userMsg);
  
  // 清空已上传图片
  uploadedImages.value = [];
  
  loading.value = true;
  streamingContent.value = '';
  streamingModel.value = '';
  streamingImages.value = [];
  
  // 创建 AbortController 用于停止流
  abortController.value = new AbortController();
  
  try {
    // 构建请求消息（不包含 preview 字段，只发送 API 需要的数据）
    const nextMessages = messages.value.map(msg => {
      const m = { role: msg.role, content: msg.content };
      if (msg.images && msg.images.length > 0) {
        m.images = msg.images.map(img => ({
          mime_type: img.mime_type,
          data: img.data
        }));
      }
      return m;
    });
    
    // 使用流式接口
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: model.value, messages: nextMessages }),
      signal: abortController.value.signal,
    });
    
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || `请求失败 (${res.status})`);
    }
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);
          if (dataStr.trim() === '[DONE]') continue;
          
          try {
            const data = JSON.parse(dataStr);
            
            if (data.error) {
              throw new Error(data.error);
            }
            
            if (data.content) {
              streamingContent.value += data.content;
            }
            if (data.model) {
              streamingModel.value = data.model;
            }
            
            // 处理图片数据
            if (data.image) {
              streamingImages.value.push(data.image);
            }
            
            if (data.done) {
              // 流结束，保存消息
              const assistantMsg = {
                role: 'assistant',
                content: streamingContent.value,
                model: streamingModel.value || model.value,
              };
              
              // 添加生成的图片
              if (streamingImages.value.length > 0) {
                assistantMsg.images = [...streamingImages.value];
              }
              
              messages.value.push(assistantMsg);
              streamingContent.value = '';
              streamingModel.value = '';
              streamingImages.value = [];
            }
            
            // 滚动到底部
            await nextTick();
            if (listRef.value) {
              listRef.value.scrollTop = listRef.value.scrollHeight;
            }
          } catch (e) {
            if (e.name !== 'SyntaxError') {
              throw e;
            }
          }
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      // 用户主动停止，不显示错误
      console.log('流式请求已取消');
    } else {
      error.value = e.message;
      // 如果已有流式内容，保存它
      if (streamingContent.value || streamingImages.value.length > 0) {
        const assistantMsg = {
          role: 'assistant',
          content: streamingContent.value + '\n\n*[响应中断]*',
          model: streamingModel.value || model.value,
        };
        if (streamingImages.value.length > 0) {
          assistantMsg.images = [...streamingImages.value];
        }
        messages.value.push(assistantMsg);
        streamingContent.value = '';
        streamingModel.value = '';
        streamingImages.value = [];
      } else {
        // 移除用户消息
        messages.value.pop();
      }
    }
  } finally {
    loading.value = false;
    abortController.value = null;
  }
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
  display: flex;
  align-items: center;
  width: 100%;
  border-radius: var(--radius-sm);
  background: transparent;
  transition: background 0.15s;
}

.conversation-item:hover {
  background: var(--surface-hover);
}

.conversation-item--active {
  background: var(--accent-muted);
}

.conversation-title-btn {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
  transition: color 0.15s;
}

.conversation-item:hover .conversation-title-btn,
.conversation-item--active .conversation-title-btn {
  color: var(--text);
}

.conversation-item--active .conversation-title-btn {
  color: var(--accent);
}

.conversation-delete-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.conversation-item:hover .conversation-delete-btn {
  opacity: 0.6;
}

.conversation-delete-btn:hover {
  opacity: 1 !important;
}

.conversation-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

/* Markdown 渲染样式 */
.markdown-body {
  white-space: normal;
}

.markdown-body :deep(p) {
  margin: 0 0 1em 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: var(--surface-hover);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 1rem;
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-body :deep(code) {
  font-family: ui-monospace, 'SF Mono', 'Cascadia Code', 'Segoe UI Mono', monospace;
  font-size: 0.875em;
}

.markdown-body :deep(:not(pre) > code) {
  background: var(--surface-hover);
  padding: 0.125em 0.375em;
  border-radius: 4px;
  color: var(--accent);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.markdown-body :deep(li) {
  margin: 0.25em 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--accent);
  margin: 1em 0;
  padding-left: 1em;
  color: var(--text-secondary);
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 1em 0;
  width: 100%;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 0.5em 0.75em;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--surface-hover);
  font-weight: 600;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 1.25em 0 0.5em 0;
  font-weight: 600;
}

.markdown-body :deep(h1) { font-size: 1.5em; }
.markdown-body :deep(h2) { font-size: 1.25em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.5em 0;
}

/* Toast 错误提示 */
.toast {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  margin: 0 1rem 0.5rem;
  border-radius: var(--radius-md);
  max-width: 45rem;
  margin-left: auto;
  margin-right: auto;
}

.toast--error {
  background: var(--error-bg);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.toast-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.toast-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  min-width: 0;
}

.toast-message strong {
  display: block;
  color: var(--error);
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.toast-message p {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  word-break: break-word;
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.toast-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text);
}

.footer {
  flex-shrink: 0;
  padding: 1.25rem 1.5rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-top: 1px solid var(--border-subtle);
  position: relative;
  transition: background 0.2s, border-color 0.2s;
}

.footer--dragover {
  background: var(--accent-muted);
  border-top-color: var(--accent);
}

/* ----- 拖拽覆盖层 ----- */
.drop-overlay {
  position: absolute;
  inset: 0;
  background: rgba(var(--accent-rgb, 99, 102, 241), 0.1);
  border: 2px dashed var(--accent);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
  animation: dropPulse 1s ease-in-out infinite;
}

@keyframes dropPulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.drop-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: var(--accent);
  font-size: 0.9375rem;
  font-weight: 500;
}

.drop-icon {
  font-size: 2rem;
  animation: dropBounce 0.6s ease-in-out infinite;
}

@keyframes dropBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
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

.send-btn,
.stop-btn {
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.send-btn {
  background: var(--accent);
  color: #fff;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stop-btn {
  background: var(--error);
  color: #fff;
}

.stop-btn:hover {
  background: #dc2626;
}

/* ----- 图片上传与预览 ----- */
.hidden-file-input {
  display: none;
}

.upload-btn {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--surface-hover);
  color: var(--text-secondary);
  font-size: 1.125rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn:hover:not(:disabled) {
  background: var(--accent-muted);
  color: var(--accent);
}

.upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.uploaded-images-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  max-width: 45rem;
  width: 100%;
  margin-bottom: 0.75rem;
}

.uploaded-image-item {
  position: relative;
  width: 4rem;
  height: 4rem;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
}

.uploaded-image-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image-btn {
  position: absolute;
  top: 0.125rem;
  right: 0.125rem;
  width: 1.25rem;
  height: 1.25rem;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 0.875rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.remove-image-btn:hover {
  background: var(--error);
}

/* ----- 消息中的图片 ----- */
.block-images {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.block-image {
  max-width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}

.block-image--user {
  max-height: 8rem;
  object-fit: contain;
}

.block-image--generated {
  max-height: 24rem;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.block-image--generated:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.generated-image-wrap {
  position: relative;
  display: inline-block;
}

.download-btn {
  position: absolute;
  bottom: 0.5rem;
  right: 0.5rem;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}

.generated-image-wrap:hover .download-btn {
  opacity: 1;
}

.download-btn:hover {
  background: var(--accent);
}

/* 侧边栏遮罩（移动端） */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 8;
}

/* 删除确认模态框 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  max-width: 24rem;
  width: 90%;
}

.modal h3 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.modal p {
  margin: 0 0 1.25rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-cancel,
.btn-danger {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  background: var(--surface-hover);
  color: var(--text);
}

.btn-cancel:hover {
  background: var(--border);
}

.btn-danger {
  background: var(--error);
  color: #fff;
}

.btn-danger:hover {
  background: #dc2626;
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