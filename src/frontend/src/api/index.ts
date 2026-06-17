import axios from 'axios'
import type { PageResponse, Document, DocumentDetail, DocumentChunk, Session, Message, Skill, McpServer, McpTool, Tool } from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 知识库 API
export const knowledgeApi = {
  // 上传文档 — 后端可能立即返回(异步处理)，这里给长超时
  uploadDocument: async (file: File, name?: string): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)
    if (name) {
      formData.append('name', name)
    }
    const response = await api.post('/knowledge/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000, // 大文件上传给 2 分钟
    })
    return response.data.data
  },

  // 获取文档列表
  getDocuments: async (page: number = 1, pageSize: number = 10, keyword?: string, type?: string): Promise<PageResponse<Document>> => {
    const params: Record<string, string | number> = { page, pageSize }
    if (keyword) params.keyword = keyword
    if (type) params.type = type
    const response = await api.get('/knowledge/documents', { params })
    return response.data.data
  },

  // 获取文档详情
  getDocument: async (id: string): Promise<DocumentDetail> => {
    const response = await api.get(`/knowledge/documents/${id}`)
    return response.data.data
  },

  // 获取文档分块
  getDocumentChunks: async (id: string): Promise<DocumentChunk[]> => {
    const response = await api.get(`/knowledge/documents/${id}/chunks`)
    return response.data.data
  },

  // 删除文档
  deleteDocument: async (id: string): Promise<void> => {
    await api.delete(`/knowledge/documents/${id}`)
  }
}

// 聊天 API (SSE streaming enabled)
export const chatApi = {
  // 创建会话
  createSession: async (title: string): Promise<Session> => {
    const response = await api.post('/chat/sessions', { title })
    return response.data.data
  },

  // 获取会话列表
  getSessions: async (page: number = 1, pageSize: number = 10): Promise<PageResponse<Session>> => {
    const response = await api.get('/chat/sessions', {
      params: { page, pageSize }
    })
    return response.data.data
  },

  // 获取会话详情
  getSession: async (id: string): Promise<Session> => {
    const response = await api.get(`/chat/sessions/${id}`)
    return response.data.data
  },

  // 获取会话消息
  getSessionMessages: async (id: string): Promise<Message[]> => {
    const response = await api.get(`/chat/sessions/${id}/messages`)
    return response.data.data
  },

  // 发送消息（流式输出）- 返回一个包含事件处理器和中止函数的对象
  sendMessageStream: (sessionId: string, content: string, skillIds?: string[], toolIds?: string[]): Promise<{ on: (event: string, handler: (data: any) => void) => void; abort: () => void }> => {
    let abortController: AbortController | null = null

    return new Promise((resolve, reject) => {
      abortController = new AbortController()
      const eventHandlers: Map<string, (data: any) => void> = new Map()

      fetch(`/api/v1/chat/sessions/${sessionId}/messages/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json;charset=UTF-8'
        },
        body: JSON.stringify({ content, skillIds, toolIds }),
        signal: abortController.signal
      }).then(response => {
        if (!response.ok) {
          reject(new Error('Failed to connect: ' + response.statusText))
          return
        }
        
        const reader = response.body?.getReader()
        const decoder = new TextDecoder('UTF-8')
        
        if (!reader) {
          reject(new Error('No reader available'))
          return
        }
        
        const processStream = async () => {
          let buffer = ''

          try {
            while (true) {
              const { done, value } = await reader.read()
              
              if (done) break
              
              const chunk = decoder.decode(value, { stream: true })
              buffer += chunk
              
              let newlineIdx = buffer.indexOf('\n\n')
              while (newlineIdx !== -1) {
                const block = buffer.substring(0, newlineIdx)
                buffer = buffer.substring(newlineIdx + 2)
                
                if (!block.trim()) {
                  newlineIdx = buffer.indexOf('\n\n')
                  continue
                }
                
                let eventName = 'message'
                let dataLines: string[] = []
                
                const lines = block.split('\n')
                for (const line of lines) {
                  if (line.startsWith('event:')) {
                    eventName = line.substring(6).trim()
                  } else if (line.startsWith('data:')) {
                    dataLines.push(line.substring(5).trim())
                  }
                }
                
                if (dataLines.length > 0) {
                  const dataStr = dataLines.join('\n')
                  if (!dataStr) {
                    newlineIdx = buffer.indexOf('\n\n')
                    continue
                  }
                  
                  let parsedData: any = dataStr
                  if (dataStr.startsWith('{') || dataStr.startsWith('[')) {
                    try {
                      parsedData = JSON.parse(dataStr)
                    } catch (e) {
                      // Keep as string
                    }
                  }
                  
                  const handler = eventHandlers.get(eventName)
                  if (handler) {
                    try {
                      handler(parsedData)
                    } catch (e) {
                      console.error(`Error in ${eventName} handler:`, e)
                    }
                  }
                }
                
                newlineIdx = buffer.indexOf('\n\n')
              }
            }
          } catch (e: any) {
            if (e.name !== 'AbortError') {
              console.error('Stream error:', e)
              const errorHandler = eventHandlers.get('error')
              if (errorHandler) {
                errorHandler(e.message || 'Stream connection error')
              }
            }
          } finally {
            reader.releaseLock()
          }
        }
        
        // 先 resolve，让调用方注册 .on() 事件处理器
        resolve({ 
          on: (event: string, handler: (data: any) => void) => {
            eventHandlers.set(event, handler)
          },
          abort: () => {
            if (abortController) {
              abortController.abort()
            }
          }
        })
        
        // 延迟到下一个宏任务启动流处理，确保 .on() 处理器已注册
        setTimeout(() => {
          processStream().catch(console.error)
        }, 0)
        
      }).catch(error => {
        reject(error)
      })
    })
  },

  // 发送消息（同步版本，保留向后兼容）
  sendMessage: async (sessionId: string, content: string): Promise<Message> => {
    const response = await api.post(`/chat/sessions/${sessionId}/messages`, {
      content
    })
    return response.data.data
  },

  // 删除会话
  deleteSession: async (id: string): Promise<void> => {
    await api.delete(`/chat/sessions/${id}`)
  }
}

// ======== Skill API ========

export const skillApi = {
  getSkills: async (page = 1, pageSize = 20, keyword?: string, category?: string): Promise<PageResponse<Skill>> => {
    const params: Record<string, string | number> = { page, pageSize }
    if (keyword) params.keyword = keyword
    if (category) params.category = category
    const res = await api.get('/skills', { params })
    return res.data.data
  },

  getSkill: async (id: string): Promise<Skill> => {
    const res = await api.get(`/skills/${id}`)
    return res.data.data
  },

  getEnabledSkills: async (): Promise<Skill[]> => {
    const res = await api.get('/skills/enabled')
    return res.data.data
  },

  createSkill: async (skill: Partial<Skill>): Promise<Skill> => {
    const res = await api.post('/skills', skill)
    return res.data.data
  },

  updateSkill: async (id: string, skill: Partial<Skill>): Promise<Skill> => {
    const res = await api.put(`/skills/${id}`, skill)
    return res.data.data
  },

  deleteSkill: async (id: string): Promise<void> => {
    await api.delete(`/skills/${id}`)
  },

  importSkill: async (file: File): Promise<Skill> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post('/skills/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return res.data.data
  }
}

// ======== MCP API ========

export const mcpApi = {
  getServers: async (): Promise<McpServer[]> => {
    const res = await api.get('/mcp/servers')
    return res.data.data
  },

  getEnabledServers: async (): Promise<McpServer[]> => {
    const res = await api.get('/mcp/servers/enabled')
    return res.data.data
  },

  getServer: async (id: string): Promise<McpServer> => {
    const res = await api.get(`/mcp/servers/${id}`)
    return res.data.data
  },

  createServer: async (server: Partial<McpServer>): Promise<McpServer> => {
    const res = await api.post('/mcp/servers', server)
    return res.data.data
  },

  updateServer: async (id: string, server: Partial<McpServer>): Promise<McpServer> => {
    const res = await api.put(`/mcp/servers/${id}`, server)
    return res.data.data
  },

  deleteServer: async (id: string): Promise<void> => {
    await api.delete(`/mcp/servers/${id}`)
  },

  testConnection: async (id: string): Promise<string> => {
    const res = await api.post(`/mcp/servers/${id}/test`)
    return res.data.data
  },

  getServerTools: async (serverId: string): Promise<McpTool[]> => {
    const res = await api.get(`/mcp/servers/${serverId}/tools`)
    return res.data.data
  },

  getEnabledTools: async (): Promise<McpTool[]> => {
    const res = await api.get('/mcp/tools/enabled')
    return res.data.data
  },

  discoverTools: async (serverId: string): Promise<McpTool[]> => {
    const res = await api.post(`/mcp/servers/${serverId}/discover`)
    return res.data.data
  },

  toggleTool: async (toolId: string, enabled: boolean): Promise<McpTool> => {
    const res = await api.put(`/mcp/tools/${toolId}/toggle`, { enabled })
    return res.data.data
  },

  callTool: async (toolId: string, args: Record<string, any>): Promise<string> => {
    const res = await api.post(`/mcp/tools/${toolId}/call`, args)
    return res.data.data
  }
}

export default api

// ======== Tool API ========

export const toolsApi = {
  getTools: async (page = 1, pageSize = 20, keyword?: string, toolType?: string): Promise<PageResponse<Tool>> => {
    const params: Record<string, string | number> = { page, pageSize }
    if (keyword) params.keyword = keyword
    if (toolType) params.toolType = toolType
    const res = await api.get('/tools', { params })
    return res.data.data
  },

  getTool: async (id: string): Promise<Tool> => {
    const res = await api.get(`/tools/${id}`)
    return res.data.data
  },

  getEnabledTools: async (): Promise<Tool[]> => {
    const res = await api.get('/tools/enabled')
    return res.data.data
  },

  createTool: async (tool: Partial<Tool>): Promise<Tool> => {
    const res = await api.post('/tools', tool)
    return res.data.data
  },

  updateTool: async (id: string, tool: Partial<Tool>): Promise<Tool> => {
    const res = await api.put(`/tools/${id}`, tool)
    return res.data.data
  },

  deleteTool: async (id: string): Promise<void> => {
    await api.delete(`/tools/${id}`)
  }
}