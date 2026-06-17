<template>
  <div class="tool-page">
    <el-card class="tool-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-blue"><Tools /></el-icon>
            <span class="header-title">工具管理</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="handleCreate">
              <el-icon :size="16"><Plus /></el-icon>新建工具
            </el-button>
          </div>
        </div>
      </template>

      <div class="search-area">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索工具名称..."
          clearable
          class="search-input"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="searchType" placeholder="类型筛选" clearable class="type-select" @change="handleSearch">
          <el-option label="函数" value="function" />
          <el-option label="API" value="api" />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <el-table :data="tools" v-loading="loading" stripe empty-text="暂无工具">
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => handleToggle(row, v)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="toolType" label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.toolType === 'function' ? 'primary' : 'success'" size="small">{{ row.toolType === 'function' ? '函数' : 'API' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="170">
          <template #default="{ row }">{{ formatDate(row.updatedAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadTools"
        @current-change="loadTools"
        class="pagination"
      />
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingTool ? '编辑工具' : '新建工具'" width="620px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="工具名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="简短描述该工具的功能" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.toolType" placeholder="选择类型" style="width:100%">
            <el-option label="函数" value="function" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数定义" required>
          <el-input
            v-model="form.parameters"
            type="textarea"
            :rows="8"
            placeholder='参数 JSON Schema，例如：
{
  "type": "object",
  "properties": {
    "location": { "type": "string" }
  }
}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools, Plus } from '@element-plus/icons-vue'
import { toolsApi } from '@/api'
import type { Tool } from '@/types'

const tools = ref<Tool[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const searchType = ref('')

const dialogVisible = ref(false)
const editingTool = ref<Tool | null>(null)
const saving = ref(false)

const form = ref({ name: '', description: '', toolType: 'function', parameters: '' })

const loadTools = async () => {
  loading.value = true
  try {
    const res = await toolsApi.getTools(currentPage.value, pageSize.value, searchKeyword.value, searchType.value)
    tools.value = res.list
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadTools()
}

const handleCreate = () => {
  editingTool.value = null
  form.value = { name: '', description: '', toolType: 'function', parameters: '' }
  dialogVisible.value = true
}

const handleEdit = (tool: Tool) => {
  editingTool.value = tool
  form.value = {
    name: tool.name,
    description: tool.description || '',
    toolType: tool.toolType || 'function',
    parameters: tool.parameters || ''
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name || !form.value.parameters) {
    ElMessage.warning('名称和参数定义不能为空')
    return
  }
  saving.value = true
  try {
    if (editingTool.value) {
      await toolsApi.updateTool(editingTool.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await toolsApi.createTool(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadTools()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleToggle = async (tool: Tool, enabled: boolean) => {
  try {
    await toolsApi.updateTool(tool.id, { enabled })
    tool.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (tool: Tool) => {
  try {
    await ElMessageBox.confirm('确定删除此工具？', '提示', { type: 'warning' })
    await toolsApi.deleteTool(tool.id)
    ElMessage.success('删除成功')
    loadTools()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

const formatDate = (date: string) => new Date(date).toLocaleString('zh-CN')

onMounted(loadTools)
</script>

<style scoped>
.tool-page { height: calc(100vh - 48px); }
.tool-card { height: 100%; display: flex; flex-direction: column; }
.tool-card :deep(.el-card__body) { flex: 1; overflow: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-title { font-size: 15px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }
.icon-blue { color: #3b82f6; }
.search-area { display: flex; gap: 8px; margin-bottom: 16px; }
.search-input { width: 240px; }
.type-select { width: 140px; }
.name-cell { display: flex; align-items: center; gap: 6px; }
.name-text { font-weight: 500; }
.pagination { padding: 16px 0 0; display: flex; justify-content: flex-end; }
</style>
