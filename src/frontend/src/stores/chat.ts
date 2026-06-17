import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api'
import type { Session, Message } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref('')
  const currentSession = ref<Session | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const sending = ref(false)

  async function loadSessions() {
    try {
      const res = await chatApi.getSessions(1, 50)
      sessions.value = res.list
    } catch (e) {
      console.warn('loadSessions failed', e)
    }
  }

  async function createSession(title: string): Promise<Session> {
    const session = await chatApi.createSession(title)
    sessions.value.unshift(session)
    return session
  }

  async function selectSession(sessionId: string) {
    currentSessionId.value = sessionId
    currentSession.value = await chatApi.getSession(sessionId)
    messages.value = await chatApi.getSessionMessages(sessionId)
  }

  async function deleteSession(sessionId: string) {
    await chatApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = ''
      currentSession.value = null
      messages.value = []
    }
  }

  function addMessage(msg: Message) {
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx >= 0) {
      messages.value.splice(idx, 1, msg)
    } else {
      messages.value.push(msg)
    }
  }

  return {
    sessions, currentSessionId, currentSession, messages, loading, sending,
    loadSessions, createSession, selectSession, deleteSession, addMessage
  }
})
