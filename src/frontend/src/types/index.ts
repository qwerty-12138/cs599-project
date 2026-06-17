export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageResponse<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export interface Document {
  id: string
  name: string
  type: string
  size: number
  chunkCount: number
  status: string
  createdAt: string
  updatedAt: string
}

export interface DocumentDetail extends Document {
  chunks: DocumentChunk[]
}

export interface DocumentChunk {
  id: string
  chunkIndex: number
  content: string
}

export interface Session {
  id: string
  title: string
  lastMessage: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

export interface Message {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  createdAt: string
}

export interface Source {
  documentId: string
  documentName: string
  chunkId: string
  content: string
  score: number
}

// ======== Skill & MCP Types ========

export interface Skill {
  id: string
  name: string
  description: string
  content: string
  category: string
  enabled: boolean
  icon: string
  sourcePath: string
  createdAt: string
  updatedAt: string
}

export interface McpServer {
  id: string
  name: string
  description: string
  url: string
  transportType: 'SSE' | 'STREAMABLE_HTTP' | 'STDIO'
  enabled: boolean
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR'
  configJson: string
  command: string
  createdAt: string
  updatedAt: string
}

export interface McpTool {
  id: string
  server: McpServer
  name: string
  description: string
  inputSchema: string
  enabled: boolean
  discoveredAt: string
}

// ======== Tool 类型 ========

export interface Tool {
  id: string
  name: string
  description: string
  toolType: string
  parameters: string
  enabled: boolean
  createdAt: string
  updatedAt: string
}