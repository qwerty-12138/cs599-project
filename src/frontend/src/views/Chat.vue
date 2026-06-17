<template>
  <div class="chat-page">
    <!-- 左侧会话列表 -->
    <el-card class="session-list-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-blue"><ChatLineSquare /></el-icon>
            <span class="header-title">会话列表</span>
          </div>
          <el-button type="primary" size="small" @click="handleCreateSession" class="create-btn">
            <el-icon :size="16"><Plus /></el-icon>
            <span>新建会话</span>
          </el-button>
        </div>
      </template>

      <el-scrollbar height="calc(100vh - 280px)" class="session-scrollbar">
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="['session-item', { active: currentSessionId === session.id }]"
          @click="handleSelectSession(session.id)"
        >
          <div class="session-icon">
            <el-icon :size="20"><ChatDotRound /></el-icon>
          </div>
          <div class="session-info">
            <div class="session-title">{{ session.title }}</div>
            <div class="session-meta">
              <span class="message-count">{{ session.messageCount }} 条消息</span>
              <span class="session-date">{{ formatDate(session.createdAt) }}</span>
            </div>
          </div>
          <el-button
            type="danger"
            size="small"
            link
            class="delete-btn"
            @click.stop="handleDeleteSession(session.id)"
          >
            <el-icon :size="16"><Delete /></el-icon>
          </el-button>
        </div>
        <div v-if="sessions.length === 0" class="empty-sessions">
          <el-icon :size="48" class="empty-icon"><ChatLineSquare /></el-icon>
          <p>暂无会话</p>
          <p class="empty-hint">点击右上角按钮创建新会话</p>
        </div>
      </el-scrollbar>
    </el-card>

    <!-- 右侧聊天区域 -->
    <el-card class="chat-area-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-green"><Service /></el-icon>
            <span class="header-title">{{ currentSession?.title || '智能问答' }}</span>
          </div>
          <div v-if="currentSession" class="header-actions">
            <el-button size="small" text @click="handleCreateSession">
              <el-icon :size="16"><Refresh /></el-icon>
              <span>新会话</span>
            </el-button>
          </div>
        </div>
      </template>

      <div class="chat-container" v-if="currentSessionId">
        <!-- 消息列表 -->
        <el-scrollbar ref="messageScrollbar" class="message-list">
          <div class="message-wrapper">
            <div
              v-for="message in messages"
              :key="message.id"
              :class="['message-item', message.role]"
            >
              <div class="message-avatar">
                <div :class="['avatar', message.role]">
                  <el-icon v-if="message.role === 'user'" :size="24"><User /></el-icon>
                  <el-icon v-else :size="24"><Service /></el-icon>
                </div>
              </div>
              <div class="message-bubble">
                <div class="message-header">
                  <span class="sender-name">{{ message.role === 'user' ? '我' : 'AI 助手' }}</span>
                  <span class="message-time">{{ formatTime(message.createdAt) }}</span>
                </div>
                <div class="message-content" :key="message.id + '-' + renderKey">
                    <template v-if="message.role === 'assistant' && message.content === '' && analyzingIntent">
                      <div class="intent-analysis">
                        <el-icon :size="20" class="gear-icon"><Setting /></el-icon>
                        <span class="analysis-text">正在分析意图...</span>
                      </div>
                    </template>
                    <template v-else>
                      <div v-html="renderMarkdown(message.content)"></div>
                    </template>
                  </div>
                <!-- 引用来源 -->
                <div v-if="message.sources && message.sources.length > 0" class="message-sources">
                  <el-collapse class="sources-collapse">
                    <el-collapse-item title="📚 引用来源" name="sources">
                      <div
                        v-for="source in message.sources"
                        :key="source.chunkId"
                        class="source-item"
                      >
                        <div class="source-header">
                          <el-tag size="small" type="primary">{{ source.documentName }}</el-tag>
                          <span class="source-score">相关性: {{ (source.score * 100).toFixed(0) }}%</span>
                        </div>
                        <div class="source-content">{{ source.content }}</div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-wrapper">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="2"
              placeholder="输入您的问题，按 Ctrl+Enter 发送..."
              :disabled="sending"
              class="chat-input"
              @keyup.ctrl.enter="handleSendMessage"
            />
          </div>
          <div class="input-actions">
            <div class="input-actions-left">
              <el-popover placement="top-start" :width="300" trigger="click" @show="loadSkills">
                <template #reference>
                  <el-button size="small" text class="mcp-toggle-btn">
                    <el-icon :size="14"><MagicStick /></el-icon>
                    <span>Skills</span>
                    <el-tag size="small" type="warning" effect="plain" style="margin-left:4px">
                      {{ enabledSkillIds.length }}/{{ availableSkills.length }}
                    </el-tag>
                  </el-button>
                </template>
                <div class="mcp-popover-list">
                  <div v-if="availableSkills.length === 0" class="mcp-popover-empty">
                    暂无 Skill
                  </div>
                  <div v-else>
                    <div v-for="skill in availableSkills" :key="skill.id" class="mcp-popover-item">
                      <el-checkbox
                        :checked="enabledSkillIds.includes(skill.id)"
                        @click.stop="toggleSkill(skill.id)"
                      >
                        <span class="mcp-popover-name">{{ skill.icon || '🧠' }} {{ skill.name }}</span>
                      </el-checkbox>
                    </div>
                  </div>
                </div>
              </el-popover>

              <el-popover placement="top-start" :width="360" trigger="click" @show="loadMcpTools">
                <template #reference>
                  <el-button size="small" text class="mcp-toggle-btn">
                    <el-icon :size="14"><SetUp /></el-icon>
                    <span>MCP 工具</span>
                    <el-tag size="small" type="success" effect="plain" style="margin-left:4px">
                      {{ enabledToolIds.length }}/{{ availableTools.length }}
                    </el-tag>
                  </el-button>
                </template>
                <div class="mcp-popover-list">
                  <div v-if="availableTools.length === 0" class="mcp-popover-empty">
                    暂无 MCP 工具，请先到 MCP 配置页发现工具
                  </div>
                  <div v-else>
                    <div class="mcp-popover-header">
                      <el-checkbox
                        :model-value="enabledToolIds.length === availableTools.length && availableTools.length > 0"
                        :indeterminate="enabledToolIds.length > 0 && enabledToolIds.length < availableTools.length"
                        @change="(val: boolean) => handleAllToolsCheck(val)"
                      >
                        <span class="mcp-select-all-label">全选</span>
                      </el-checkbox>
                    </div>
                    <div v-for="tool in availableTools" :key="tool.id" class="mcp-popover-item">
                      <el-checkbox
                        :model-value="enabledToolIds.includes(tool.id)"
                        @change="(val: boolean) => handleToolCheck(tool.id, val)"
                      >
                        <span class="mcp-popover-name">🔧 {{ tool.name }}</span>
                        <span class="mcp-tool-desc">{{ tool.description }}</span>
                      </el-checkbox>
                    </div>
                  </div>
                </div>
              </el-popover>

              <el-popover placement="top-start" :width="360" trigger="click" @show="loadMcpServers">
                <template #reference>
                  <el-button size="small" text class="mcp-toggle-btn">
                    <el-icon :size="14"><Connection /></el-icon>
                    <span>MCP 服务器</span>
                    <el-tag size="small" :type="connectedServerCount > 0 ? 'success' : 'info'" effect="plain" style="margin-left:4px">
                      {{ connectedServerCount }}/{{ availableServers.length }}
                    </el-tag>
                  </el-button>
                </template>
                <div class="mcp-popover-list">
                  <div v-if="availableServers.length === 0" class="mcp-popover-empty">
                    暂无 MCP 服务器配置，请先到 MCP 配置页添加
                  </div>
                  <div v-else>
                    <div v-for="server in availableServers" :key="server.id" class="mcp-popover-item">
                      <el-switch
                        :model-value="server.enabled"
                        :loading="togglingServerId === server.id"
                        size="small"
                        style="margin-right:4px"
                        @click.stop="toggleServer(server)"
                      />
                      <span class="mcp-popover-name" :class="{ 'text-disabled': !server.enabled }">{{ server.name }}</span>
                      <el-tag v-if="server.status === 'CONNECTED'" size="small" type="success" effect="plain" style="margin-left:auto">已连接</el-tag>
                      <el-tag v-else size="small" type="danger" effect="plain" style="margin-left:auto">断开</el-tag>
                    </div>
                  </div>
                </div>
              </el-popover>
            </div>
            <div class="input-actions-right">
              <el-button
                type="danger"
                :disabled="!sending"
                @click="handleStopGeneration"
                class="stop-btn"
              >
                <el-icon :size="18"><CircleClose /></el-icon>
                <span>停止生成</span>
              </el-button>
              <el-button
                type="primary"
                :loading="sending && !stopping"
                :disabled="!inputMessage.trim() || sending"
                @click="handleSendMessage"
                class="send-btn"
              >
                <el-icon :size="18"><Position /></el-icon>
                <span>发送</span>
              </el-button>
            </div>
          </div>

          <div class="input-hint">
            <span class="hint-text">💡 提示：支持基于知识库内容的智能问答</span>
          </div>
        </div>
      </div>

      <div class="empty-chat" v-else>
        <div class="empty-content">
          <div class="empty-icon-wrapper">
            <el-icon :size="80" class="main-icon"><MagicStick /></el-icon>
          </div>
          <h3>智能问答助手</h3>
          <p>选择一个会话开始对话，或创建新的会话</p>
          <el-button type="primary" @click="handleCreateSession" class="start-btn">
            <el-icon><Plus /></el-icon>
            <span>开始新对话</span>
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
import { Plus, Delete, ChatDotRound, Service, Refresh, User, Position, MagicStick, ChatLineSquare, CircleClose, Connection, SetUp, Setting } from '@element-plus/icons-vue'
import { chatApi, mcpApi, skillApi } from '@/api'
import type { Session, Message, McpServer, McpTool, Skill } from '@/types'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 初始化 Markdown 渲染器
const md: MarkdownIt = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  highlight: function (str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>'
      } catch (e) {
        // ignore
      }
    }
    const markdownItInstance: MarkdownIt = md
    return '<pre class="hljs"><code>' + markdownItInstance.utils.escapeHtml(str) + '</code></pre>'
  }
})

// Markdown 渲染函数
const renderMarkdown = (text: string): string => {
  if (!text) return ''
  return md.render(text)
}

const sessions = ref<Session[]>([])
const currentSessionId = ref('')
const currentSession = ref<Session | null>(null)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const sending = ref(false)
const stopping = ref(false)
const messageScrollbar = ref()
const renderKey = ref(0) // 强制 Markdown 重新渲染
const analyzingIntent = ref(false) // 意图分析中
let currentAbort: (() => void) | null = null

// ======== Skill / MCP 开关 ========
const availableServers = ref<McpServer[]>([])
const availableSkills = ref<Skill[]>([])
const availableTools = ref<McpTool[]>([])
const enabledToolIds = ref<string[]>([])
const enabledSkillIds = computed(() =>
  availableSkills.value.filter(s => s.enabled).map(s => s.id)
)
const togglingServerId = ref<string | null>(null)

const loadSkills = async () => {
  try {
    const res = await skillApi.getSkills(1, 100)
    availableSkills.value = res.list
  } catch (e) {
    console.warn('Failed to load skills', e)
  }
}

const loadMcpServers = async () => {
  try {
    availableServers.value = await mcpApi.getServers()
  } catch (e) {
    console.warn('Failed to load servers', e)
  }
}

const loadMcpTools = async () => {
  try {
    availableTools.value = await mcpApi.getEnabledTools()
  } catch (e) {
    console.warn('Failed to load MCP tools', e)
  }
}

const handleToolCheck = (toolId: string, checked: boolean) => {
  if (checked) {
    if (!enabledToolIds.value.includes(toolId)) {
      enabledToolIds.value.push(toolId)
    }
  } else {
    const idx = enabledToolIds.value.indexOf(toolId)
    if (idx >= 0) enabledToolIds.value.splice(idx, 1)
  }
}

const handleAllToolsCheck = (checked: boolean) => {
  if (checked) {
    const allIds = availableTools.value.map(t => t.id)
    enabledToolIds.value.splice(0, enabledToolIds.value.length, ...allIds)
  } else {
    enabledToolIds.value.splice(0)
  }
}

// Skill 启用/禁用（与 Skill 管理页同步后端 enabled 字段）
const toggleSkill = async (skillId: string) => {
  const skill = availableSkills.value.find(s => s.id === skillId)
  if (!skill) return
  try {
    await skillApi.updateSkill(skillId, { enabled: !skill.enabled })
    skill.enabled = !skill.enabled
    ElMessage.success(skill.enabled ? 'Skill 已启用' : 'Skill 已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败')
  }
}

const connectedServerCount = computed(() =>
  availableServers.value.filter(s => s.enabled).length
)

// 切换 MCP 服务器启用/禁用（与 MCP 配置页状态同步）
const toggleServer = async (server: McpServer) => {
  togglingServerId.value = server.id
  const newEnabled = !server.enabled
  try {
    await mcpApi.updateServer(server.id, { enabled: newEnabled })
    server.enabled = newEnabled
    ElMessage.success(newEnabled ? '服务器已启用，正在加载工具...' : '服务器已禁用，正在移除工具...')
    await loadMcpTools()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  } finally {
    togglingServerId.value = null
  }
}

const LAST_SESSION_KEY = 'lastSessionId'

// 保存最后访问的会话 ID
const saveLastSession = (sessionId: string) => {
  localStorage.setItem(LAST_SESSION_KEY, sessionId)
}

// 清除最后访问的会话 ID
const clearLastSession = () => {
  localStorage.removeItem(LAST_SESSION_KEY)
}

// 加载会话列表
const loadSessions = async () => {
  try {
    const response = await chatApi.getSessions(1, 50)
    sessions.value = response.list
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '加载会话失败')
  }
}

// 创建会话
const handleCreateSession = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入会话标题', '新建会话', {
      inputPattern: /\S+/,
      inputErrorMessage: '标题不能为空',
      confirmButtonText: '创建',
      cancelButtonText: '取消'
    })
    const session = await chatApi.createSession(value)
    sessions.value.unshift(session)
    handleSelectSession(session.id)
    ElMessage.success('创建成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '创建失败')
    }
  }
}

// 选择会话
const handleSelectSession = async (sessionId: string) => {
  currentSessionId.value = sessionId
  saveLastSession(sessionId)
  try {
    currentSession.value = await chatApi.getSession(sessionId)
    messages.value = await chatApi.getSessionMessages(sessionId)
    scrollToBottom()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '加载消息失败')
  }
}

// 发送消息（流式输出）
const handleSendMessage = async () => {
  if (!inputMessage.value.trim() || !currentSessionId.value) {
    return
  }

  const content = inputMessage.value.trim()
  inputMessage.value = ''
  sending.value = true
  stopping.value = false

  // 添加用户消息
  const userMessage: Message = {
    id: 'temp-user-' + Date.now(),
    sessionId: currentSessionId.value,
    role: 'user',
    content: content,
    sources: [],
    createdAt: new Date().toISOString()
  }
  messages.value.push(userMessage)
  await nextTick()
  scrollToBottom()

  // 添加助手消息占位
  const assistantMessage: Message = {
    id: 'temp-assistant-' + Date.now(),
    sessionId: currentSessionId.value,
    role: 'assistant',
    content: '',
    sources: [],
    createdAt: new Date().toISOString()
  }
  messages.value.push(assistantMessage)
  await nextTick()
  scrollToBottom()

  // 设置意图分析状态
  analyzingIntent.value = true

  try {
      const activeSkillIds = [...enabledSkillIds.value]
      const activeToolIds = [...enabledToolIds.value]
      const stream = await chatApi.sendMessageStream(
        currentSessionId.value,
        content,
        activeSkillIds.length > 0 ? activeSkillIds : undefined,
        activeToolIds.length > 0 ? activeToolIds : undefined
      )
      currentAbort = stream.abort

      stream.on('token', (data: any) => {
        if (stopping.value) return
        analyzingIntent.value = false
        const idx = messages.value.findIndex(m => m.id === assistantMessage.id)
        if (idx !== -1) {
          messages.value[idx] = {
            ...messages.value[idx],
            content: messages.value[idx].content + data.content
          }
          nextTick(() => scrollToBottom())
        }
      })

      stream.on('tool_start', (_data: any) => {
        if (stopping.value) return
        analyzingIntent.value = false
      })

      stream.on('tool_end', (_data: any) => {
        if (stopping.value) return
      })

      stream.on('error', (data: string) => {
        if (stopping.value) return
        analyzingIntent.value = false
        ElMessage.error(data)
        const idx = messages.value.findIndex(m => m.id === assistantMessage.id)
        if (idx !== -1) messages.value[idx].content = '抱歉，发生了错误：' + data
        sending.value = false
        stopping.value = false
        currentAbort = null
      })

      stream.on('done', (_data: any) => {
        if (stopping.value) return
        analyzingIntent.value = false
        renderKey.value++
        sending.value = false
        stopping.value = false
        currentAbort = null
      })

      stream.on('assistantMessage', (data: any) => {
        if (stopping.value) return
        analyzingIntent.value = false
        const idx = messages.value.findIndex(m => m.id === assistantMessage.id)
        if (idx !== -1) {
          messages.value[idx].id = data.id
          messages.value[idx].sources = data.sources || []
          messages.value[idx].createdAt = data.createdAt
        }
        renderKey.value++
        sending.value = false
        stopping.value = false
        currentAbort = null
      })

      stream.on('userMessage', (data: any) => {
        if (stopping.value) return
        const idx = messages.value.findIndex(m => m.id === userMessage.id || m.id === data.id)
        if (idx !== -1) messages.value[idx].id = data.id
      })

    } catch (error: any) {
      analyzingIntent.value = false
      console.error('Stream error:', error)
      if (!stopping.value) {
        ElMessage.error(error.message || '发送失败')
        messages.value = messages.value.filter(m => m.id !== userMessage.id && m.id !== assistantMessage.id)
      }
      sending.value = false
      stopping.value = false
      currentAbort = null
    }
}

// 停止生成
const handleStopGeneration = () => {
  if (!sending.value || stopping.value) return
  
  stopping.value = true
  
  if (currentAbort) {
    currentAbort()
    currentAbort = null
  }
  
  // 保存已生成的部分内容
  const aiIdx = messages.value.findIndex(m => m.id.startsWith('temp-assistant-'))
  if (aiIdx !== -1 && messages.value[aiIdx].content) {
    messages.value[aiIdx].content += '\n\n[已停止生成]'
  }
  
  sending.value = false
  stopping.value = false
  ElMessage.info('已停止生成')
}

// 删除会话
const handleDeleteSession = async (sessionId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除该会话吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await chatApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = ''
      currentSession.value = null
      messages.value = []
      clearLastSession()
    }
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messageScrollbar.value) {
      messageScrollbar.value.setScrollTop(messageScrollbar.value.wrapRef.scrollHeight)
    }
  })
}

// 格式化日期
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// 格式化时间
const formatTime = (dateStr: string): string => {
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  await loadSessions()

  // 初始化加载 Skill 和 MCP 数据
  loadSkills()
  loadMcpServers()
  loadMcpTools()

  // 1) 优先处理来自历史页面的 sessionId 查询参数
  if (route.query.sessionId) {
    const sid = route.query.sessionId as string
    currentSessionId.value = sid
    saveLastSession(sid)
    try {
      currentSession.value = await chatApi.getSession(sid)
      messages.value = await chatApi.getSessionMessages(sid)
    } catch (e) {
      // ignore
    }
    return
  }

  // 2) 自动恢复上一次的会话（最新的会话）
  const lastSessionId = localStorage.getItem(LAST_SESSION_KEY)
  if (lastSessionId) {
    try {
      currentSession.value = await chatApi.getSession(lastSessionId)
      messages.value = await chatApi.getSessionMessages(lastSessionId)
      currentSessionId.value = lastSessionId
      saveLastSession(lastSessionId)
    } catch (e) {
      // 如果上一次的会话已被删除，自动进入最新会话
      clearLastSession()
      if (sessions.value.length > 0) {
        const latest = sessions.value[0] // 后端按 updatedAt desc 排序，第一条即最新
        handleSelectSession(latest.id)
      }
    }
  } else if (sessions.value.length > 0) {
    // 没有历史记录时，自动进入最新会话
    const latest = sessions.value[0]
    handleSelectSession(latest.id)
  }
})

// keep-alive 每次激活时刷新 Skill 和 MCP 数据（与配置页同步）
onActivated(async () => {
  availableServers.value = await mcpApi.getServers()
  loadSkills()
  loadMcpTools()
})
</script>

<style scoped>
/* == Emoji 字体增强：确保多字节 emoji 正确显示 == */
.message-content :deep(*) {
  font-family:
    'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', 'Twemoji Mozilla',
    system-ui, -apple-system, 'Microsoft YaHei', sans-serif;
}

.chat-page {
  display: flex;
  gap: 20px;
  height: calc(100vh - 48px);
}

/* ===== Session List ===== */
.session-list-card {
  width: 300px;
  flex-shrink: 0;
}

.chat-area-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
}

.icon-blue { color: var(--c-primary); }
.icon-green { color: #10b981; }

.create-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.session-scrollbar {
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all .2s ease;
  margin-bottom: 4px;
  background: #f9fafb;
}

.session-item:hover {
  background: #f3f4f6;
}

.session-item.active {
  background: rgba(99, 102, 241, .08);
  box-shadow: inset 3px 0 0 var(--c-primary);
}

.session-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-weight: 600;
  color: var(--c-text);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}

.message-count {
  font-size: 11px;
  color: #9ca3af;
}

.session-date {
  font-size: 11px;
  color: #c0c4cc;
}

.delete-btn {
  opacity: 0;
  transition: opacity .2s ease;
  padding: 4px !important;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.empty-sessions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #c0c4cc;
}

.empty-icon {
  margin-bottom: 12px;
  color: #d1d5db;
}

.empty-hint {
  font-size: 12px;
  margin-top: 6px;
}

/* ===== Chat Container ===== */
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
}

.message-list {
  flex: 1;
  padding: 20px;
  background: #fafbfd;
  border-radius: 0;
}

.message-wrapper {
  max-width: 100%;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-item.user .message-bubble {
  align-items: flex-end;
}

.message-item.user .message-content {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 16px 16px 4px 16px;
}

.message-item.assistant .message-content {
  background: white;
  border: 1px solid var(--c-border);
  border-radius: 16px 16px 16px 4px;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar.user {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.avatar.assistant {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

.message-bubble {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.message-time {
  font-size: 11px;
  color: #c0c4cc;
}

.message-content {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Markdown 内容样式 */
.message-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 6px 10px;
  text-align: left;
}

.message-content :deep(th) {
  background: #f3f4f6;
  font-weight: 600;
  color: #374151;
}

.message-content :deep(tr:hover) {
  background: #f9fafb;
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  margin: 12px 0 6px;
  color: #1f2937;
}

.message-content :deep(h2) { font-size: 16px; }
.message-content :deep(h3) { font-size: 15px; }

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.message-content :deep(li) {
  margin: 3px 0;
}

.message-content :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.message-content :deep(code) {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}

.message-content :deep(pre.hljs) {
  background: #f6f8fa;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  font-size: 13px;
}

.message-content :deep(blockquote) {
  border-left: 3px solid #6366f1;
  padding-left: 12px;
  margin: 8px 0;
  color: #6b7280;
}

.message-content :deep(a) {
  color: #6366f1;
  text-decoration: underline;
}

.message-content :deep(p) {
  margin: 4px 0;
}

.intent-analysis {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #6366f1;
}

.gear-icon {
  animation: gear-spin 1.5s linear infinite;
  color: #6366f1;
}

@keyframes gear-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.analysis-text {
  font-size: 14px;
  font-weight: 500;
  color: #6366f1;
}

.message-sources {
  margin-top: 10px;
}

.sources-collapse {
  background: transparent;
}

.source-item {
  padding: 10px;
  background: rgba(99, 102, 241, .04);
  border-radius: 8px;
  margin-bottom: 6px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.source-score {
  font-size: 11px;
  color: var(--c-primary);
  font-weight: 500;
}

.source-content {
  font-size: 12px;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 120px;
  overflow-y: auto;
  padding-right: 8px;
}

/* ===== Input Area ===== */
.input-area {
  padding: 14px 20px;
  background: white;
  border-top: 1px solid var(--c-border);
}

.input-wrapper {
  margin-bottom: 10px;
}

.chat-input {
  resize: none;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.input-actions-left {
  display: flex;
  gap: 6px;
}

.mcp-toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mcp-popover-list {
  max-height: 260px;
  overflow-y: auto;
}

.mcp-popover-header {
  display: flex;
  align-items: center;
  padding: 4px 4px 6px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 2px;
}

.mcp-select-all-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.mcp-popover-empty {
  font-size: 12px;
  color: #9ca3af;
  padding: 20px 8px;
  text-align: center;
}

.mcp-popover-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  border-bottom: 1px solid #f3f4f6;
}

.mcp-popover-item:last-child {
  border-bottom: none;
}

.mcp-popover-name {
  font-size: 13px;
  font-weight: 500;
}

.mcp-tool-desc {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.feature-toggle-info {
  display: flex;
  gap: 6px;
}

.feature-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.input-actions-right {
  display: flex;
  gap: 8px;
}

/* ===== Feature Panel ===== */
.feature-panel {
  background: #f9fafb;
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 10px;
}

.feature-group { margin-bottom: 4px; }

.feature-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.feature-empty {
  font-size: 12px;
  color: #9ca3af;
  padding: 8px 0;
}

.feature-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feature-item {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .15s;
  font-size: 13px;
}

.feature-item:hover {
  background: rgba(99, 102, 241, .06);
}

.feature-item-name {
  font-size: 13px;
}

.text-disabled {
  color: #c0c4cc;
  text-decoration: line-through;
}

.feature-divider {
  margin: 10px 0;
}

/* slide transition */
.slide-enter-active, .slide-leave-active {
  transition: all .25s ease;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.stop-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  font-size: 13px;
}

.input-hint {
  text-align: center;
  margin-top: 8px;
}

.hint-text {
  font-size: 11px;
  color: #c0c4cc;
}

/* ===== Empty State ===== */
.empty-chat {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.empty-content {
  text-align: center;
  padding: 40px;
}

.empty-icon-wrapper {
  width: 96px;
  height: 96px;
  background: linear-gradient(135deg, rgba(99,102,241,.08), rgba(139,92,246,.08));
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.main-icon {
  color: var(--c-primary);
}

.empty-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--c-text);
  margin-bottom: 6px;
}

.empty-content p {
  color: var(--c-text-secondary);
  font-size: 14px;
  margin-bottom: 20px;
}

.start-btn {
  padding: 10px 28px;
  font-size: 14px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 8px;
}
</style>