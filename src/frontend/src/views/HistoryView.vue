<template>
  <div class="history-page">
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-blue"><Clock /></el-icon>
            <span class="header-title">会话历史</span>
            <el-badge :value="total" class="badge" />
          </div>
          <el-button size="small" @click="loadSessions">
            <el-icon :size="16"><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </template>

      <div v-if="loading" class="loading-wrapper">
        <el-icon :size="32" class="loading-icon"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <template v-else>
        <div v-if="groupedSessions.length === 0" class="empty-state">
          <el-icon :size="48" class="empty-icon"><ChatLineSquare /></el-icon>
          <p>暂无会话历史</p>
          <p class="empty-hint">开始问答后，会话将自动记录在此</p>
          <router-link to="/chat">
            <el-button type="primary"><el-icon><Plus /></el-icon>开始新对话</el-button>
          </router-link>
        </div>

        <div v-for="group in groupedSessions" :key="group.label" class="session-group">
          <div class="group-label">
            <el-tag size="small" type="info" effect="plain">{{ group.label }}</el-tag>
          </div>
          <div
            v-for="session in group.sessions"
            :key="session.id"
            class="session-row"
            @click="handleOpenSession(session)"
          >
            <div class="session-icon">
              <el-icon :size="20"><ChatDotRound /></el-icon>
            </div>
            <div class="session-info">
              <div class="session-title">{{ session.title }}</div>
              <div class="session-meta">
                <span>{{ session.messageCount }} 条消息</span>
                <span class="meta-sep">·</span>
                <span>{{ formatDateTime(session.updatedAt) }}</span>
              </div>
              <div v-if="session.lastMessage" class="session-last">{{ session.lastMessage }}</div>
            </div>
            <el-button
              type="danger"
              size="small"
              link
              class="delete-btn"
              @click.stop="handleDelete(session)"
            >
              <el-icon :size="16"><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Refresh, Loading, ChatLineSquare, Plus, ChatDotRound, Delete } from '@element-plus/icons-vue'
import { chatApi } from '@/api'
import type { Session } from '@/types'

const router = useRouter()
const sessions = ref<Session[]>([])
const loading = ref(false)
const total = ref(0)

// 按时间分组
const groupedSessions = computed(() => {
  const groups: { label: string; sessions: Session[] }[] = []
  const today: Session[] = []
  const yesterday: Session[] = []
  const thisWeek: Session[] = []
  const earlier: Session[] = []

  const now = new Date()
  const todayStr = now.toDateString()
  const yesterdayDate = new Date(now)
  yesterdayDate.setDate(yesterdayDate.getDate() - 1)
  const yesterdayStr = yesterdayDate.toDateString()
  const weekAgo = new Date(now)
  weekAgo.setDate(weekAgo.getDate() - 7)

  for (const s of sessions.value) {
    const d = new Date(s.updatedAt)
    const dateStr = d.toDateString()
    if (dateStr === todayStr) {
      today.push(s)
    } else if (dateStr === yesterdayStr) {
      yesterday.push(s)
    } else if (d >= weekAgo) {
      thisWeek.push(s)
    } else {
      earlier.push(s)
    }
  }

  if (today.length) groups.push({ label: '今天', sessions: today })
  if (yesterday.length) groups.push({ label: '昨天', sessions: yesterday })
  if (thisWeek.length) groups.push({ label: '最近 7 天', sessions: thisWeek })
  if (earlier.length) groups.push({ label: '更早', sessions: earlier })

  return groups
})

const loadSessions = async () => {
  loading.value = true
  try {
    const res = await chatApi.getSessions(1, 100)
    sessions.value = res.list
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleOpenSession = (session: Session) => {
  router.push({ path: '/chat', query: { sessionId: session.id } })
}

const handleDelete = async (session: Session) => {
  try {
    await ElMessageBox.confirm('确定删除此会话？', '提示', { type: 'warning' })
    await chatApi.deleteSession(session.id)
    sessions.value = sessions.value.filter(s => s.id !== session.id)
    total.value--
    ElMessage.success('已删除')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

const formatDateTime = (dateStr: string): string => {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(loadSessions)
</script>

<style scoped>
.history-page { height: calc(100vh - 48px); }
.history-card { height: 100%; display: flex; flex-direction: column; }
.history-card :deep(.el-card__body) { flex: 1; overflow: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-title { font-size: 15px; font-weight: 600; }
.icon-blue { color: #3b82f6; }
.badge { background: linear-gradient(135deg, #6366f1, #8b5cf6); }

.loading-wrapper { display: flex; flex-direction: column; align-items: center; padding: 80px; color: #9ca3af; }
.loading-icon { animation: spin 1s linear infinite; margin-bottom: 12px; color: var(--c-primary); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: 80px; color: #c0c4cc; }
.empty-icon { margin-bottom: 12px; color: #d1d5db; }
.empty-hint { font-size: 12px; margin-top: 6px; margin-bottom: 20px; }

.session-group { margin-bottom: 20px; }
.group-label { margin-bottom: 8px; }
.session-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: 10px;
  cursor: pointer; transition: all .15s;
  margin-bottom: 4px;
}
.session-row:hover { background: rgba(99,102,241,.04); }
.session-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  color: white; flex-shrink: 0;
}
.session-info { flex: 1; min-width: 0; }
.session-title { font-weight: 600; font-size: 14px; margin-bottom: 2px; }
.session-meta { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
.meta-sep { margin: 0 4px; }
.session-last {
  font-size: 12px; color: #6b7280;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.delete-btn { opacity: 0; transition: opacity .15s; }
.session-row:hover .delete-btn { opacity: 1; }
</style>
