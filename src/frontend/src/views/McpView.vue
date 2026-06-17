<template>
  <div class="mcp-page">
    <el-card class="mcp-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-blue"><Connection /></el-icon>
            <span class="header-title">MCP 服务器配置</span>
          </div>
          <el-button type="primary" size="small" @click="handleCreate">
            <el-icon :size="16"><Plus /></el-icon>添加服务器
          </el-button>
        </div>
      </template>

      <el-table :data="servers" v-loading="loading" stripe empty-text="暂无 MCP 服务器配置">
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => handleToggleServer(row, v)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="url" label="URL" min-width="240" show-overflow-tooltip />
        <el-table-column prop="transportType" label="传输类型" width="130">
          <template #default="{ row }">
            <el-tag :type="row.transportType === 'SSE' ? 'success' : row.transportType === 'STREAMABLE_HTTP' ? 'warning' : 'info'" size="small">{{ row.transportType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'CONNECTED' ? 'success' : row.status === 'ERROR' ? 'danger' : 'info'" size="small">{{ row.status === 'CONNECTED' ? '已连接' : row.status === 'ERROR' ? '错误' : '未连接' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleTest(row)">测试</el-button>
            <el-button type="primary" link @click="handleDiscover(row)">发现工具</el-button>
            <el-button type="primary" link @click="handleViewTools(row)">工具列表</el-button>
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="dev-hint">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            MCP 通过 JSON-RPC over HTTP 协议与工具服务器通信。添加服务器后点击"发现工具"自动获取可用工具。
          </template>
        </el-alert>
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingServer ? '编辑服务器' : '添加服务器'" width="620px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="例如: 本地文件系统" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="可选描述" />
        </el-form-item>
        <el-form-item label="URL" required>
          <el-input v-model="form.url" placeholder="http://localhost:3001/mcp" />
        </el-form-item>
        <el-form-item label="传输类型">
          <el-select v-model="form.transportType" style="width:100%">
            <el-option label="SSE (Server-Sent Events)" value="SSE" />
            <el-option label="STREAMABLE_HTTP" value="STREAMABLE_HTTP" />
            <el-option label="STDIO (命令行)" value="STDIO" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.transportType === 'STDIO'" label="命令">
          <el-input v-model="form.command" placeholder="启动命令，如: npx @modelcontextprotocol/server-filesystem ./data" />
        </el-form-item>
        <el-form-item label="额外配置">
          <el-input v-model="form.configJson" type="textarea" :rows="3" placeholder='{"headers":{"Authorization":"Bearer xxx"}}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 工具列表对话框 -->
    <el-dialog v-model="toolsDialogVisible" :title="`工具列表 - ${toolsServerName}`" width="650px">
      <el-table :data="tools" v-loading="loadingTools" stripe empty-text="暂未发现工具，请先点击「发现工具」">
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => handleToggleTool(row, v)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="工具名" min-width="140" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Plus } from '@element-plus/icons-vue'
import { mcpApi } from '@/api'
import type { McpServer, McpTool } from '@/types'

const servers = ref<McpServer[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const editingServer = ref<McpServer | null>(null)
const saving = ref(false)

const form = ref({ name: '', description: '', url: '', transportType: 'SSE' as McpServer['transportType'], command: '', configJson: '' })

const toolsDialogVisible = ref(false)
const toolsServerName = ref('')
const toolsServerId = ref('')
const tools = ref<McpTool[]>([])
const loadingTools = ref(false)

const loadServers = async () => {
  loading.value = true
  try {
    servers.value = await mcpApi.getServers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  editingServer.value = null
  form.value = { name: '', description: '', url: '', transportType: 'SSE', command: '', configJson: '' }
  dialogVisible.value = true
}

const handleEdit = (server: McpServer) => {
  editingServer.value = server
  form.value = { name: server.name, description: server.description || '', url: server.url, transportType: server.transportType, command: server.command || '', configJson: server.configJson || '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name || !form.value.url) {
    ElMessage.warning('名称和 URL 不能为空')
    return
  }
  saving.value = true
  try {
    if (editingServer.value) {
      await mcpApi.updateServer(editingServer.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await mcpApi.createServer(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadServers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleToggleServer = async (server: McpServer, enabled: boolean) => {
  try {
    await mcpApi.updateServer(server.id, { enabled })
    server.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败')
  }
}

const handleTest = async (server: McpServer) => {
  try {
    ElMessage.info('测试连接中...')
    const result = await mcpApi.testConnection(server.id)
    ElMessage.success(result)
    loadServers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '连接测试失败')
  }
}

const handleDiscover = async (server: McpServer) => {
  try {
    ElMessage.info('正在发现工具...')
    const discovered = await mcpApi.discoverTools(server.id)
    ElMessage.success(`发现 ${discovered.length} 个工具`)
    loadServers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '工具发现失败')
  }
}

const handleViewTools = async (server: McpServer) => {
  toolsServerName.value = server.name
  toolsServerId.value = server.id
  loadingTools.value = true
  toolsDialogVisible.value = true
  try {
    tools.value = await mcpApi.getServerTools(server.id)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '加载失败')
  } finally {
    loadingTools.value = false
  }
}

const handleToggleTool = async (tool: McpTool, enabled: boolean) => {
  try {
    await mcpApi.toggleTool(tool.id, enabled)
    tool.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (server: McpServer) => {
  try {
    await ElMessageBox.confirm(`确定删除服务器「${server.name}」及其所有工具？`, '提示', { type: 'warning' })
    await mcpApi.deleteServer(server.id)
    ElMessage.success('删除成功')
    loadServers()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

onMounted(loadServers)
</script>

<style scoped>
.mcp-page { height: calc(100vh - 48px); }
.mcp-card { height: 100%; display: flex; flex-direction: column; }
.mcp-card :deep(.el-card__body) { flex: 1; overflow: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-title { font-size: 15px; font-weight: 600; }
.icon-blue { color: #3b82f6; }
.dev-hint { margin-top: 16px; }
</style>
