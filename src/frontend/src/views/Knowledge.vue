<template>
  <div class="knowledge-page">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-purple"><Upload /></el-icon>
            <span class="header-title">上传文档</span>
          </div>
        </div>
      </template>
      
      <div class="upload-section">
        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
        >
          <div class="upload-icon-wrapper">
            <el-icon :size="48" class="upload-icon"><Top /></el-icon>
          </div>
          <div class="upload-text">
            <p class="upload-title">拖拽文件到此处</p>
            <p class="upload-subtitle">或点击选择文件上传</p>
          </div>
          <template #tip>
            <div class="upload-tip">
              <el-tag size="small" type="info">支持格式</el-tag>
              <span>PDF、DOCX、TXT、MD</span>
              <el-tag size="small" type="warning">最大 100MB</el-tag>
            </div>
          </template>
        </el-upload>
        
        <div v-if="selectedFile" class="selected-file-info">
          <el-icon :size="18" class="file-icon"><DocumentIcon /></el-icon>
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
        </div>
        
        <el-input
          v-model="documentName"
          placeholder="文档名称（可选，默认为文件名）"
          class="document-name-input"
        />
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          @click="handleUpload"
          class="upload-btn"
        >
          <el-icon :size="18"><Upload /></el-icon>
          <span>{{ uploading ? '上传中...' : '上传文档' }}</span>
        </el-button>
      </div>
    </el-card>

    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-blue"><FolderOpened /></el-icon>
            <span class="header-title">文档列表</span>
            <el-badge :value="total" class="badge" />
          </div>
          <div class="search-area">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索文档名称..."
              clearable
              class="search-input"
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            />
            <el-select
              v-model="searchType"
              placeholder="文件类型"
              clearable
              class="type-select"
              @change="handleSearch"
            >
              <el-option label="PDF" value="pdf" />
              <el-option label="DOCX" value="docx" />
              <el-option label="TXT" value="txt" />
              <el-option label="MD" value="md" />
            </el-select>
            <el-button type="primary" @click="handleSearch" class="search-btn">
              <el-icon :size="16"><Search /></el-icon>
              <span>搜索</span>
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="documents" 
        v-loading="loading" 
        stripe
        class="document-table"
        empty-text="暂无文档，请上传新文档"
      >
        <el-table-column prop="name" label="文档名称" min-width="220">
          <template #default="{ row }">
            <div class="file-row">
              <el-icon :size="20" class="file-type-icon">
                <component :is="getFileIcon(row.type)" />
              </el-icon>
              <span class="file-name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="文件类型" width="90">
          <template #default="{ row }">
            <el-tag :type="getFileTagType(row.type)" size="small">{{ row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="文件大小" width="100">
          <template #default="{ row }">
            <span class="file-size-text">{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="chunkCount" label="分块数量" width="90">
          <template #default="{ row }">
            <el-tag size="small" class="chunk-tag">{{ row.chunkCount }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="处理状态" width="100">
          <template #default="{ row }">
            <div class="status-wrapper">
              <el-icon v-if="row.status === 'processing'" :size="16" class="status-icon loading-icon"><Loading /></el-icon>
              <el-icon v-else-if="row.status === 'ERROR'" :size="16" class="status-icon" style="color:#ef4444"><WarningFilled /></el-icon>
              <el-icon v-else :size="16" class="status-icon success-icon"><CircleCheck /></el-icon>
              <span :class="['status-text', row.status]">
                {{ row.status === 'READY' ? '已处理' : row.status === 'ERROR' ? '失败' : '处理中' }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170">
          <template #default="{ row }">
            <span class="date-text">{{ formatDate(row.createdAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" link @click="handleViewDetail(row)" class="action-btn view-btn">
                <el-icon :size="16"><View /></el-icon>
                <span>详情</span>
              </el-button>
              <el-button type="danger" link @click="handleDelete(row)" class="action-btn delete-btn">
                <el-icon :size="16"><DeleteFilled /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
        class="pagination"
      />
    </el-card>

    <!-- 文档详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="文档详情" width="700px" class="detail-dialog">
      <div class="detail-content">
        <el-descriptions :column="2" border class="document-info">
          <el-descriptions-item label="文档名称" label-width="100px">
            <div class="info-icon-wrapper">
              <el-icon :size="20" class="info-icon">
                <component :is="getFileIcon(currentDocument?.type || '')" />
              </el-icon>
              <span>{{ currentDocument?.name }}</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="文件类型" label-width="100px">
            <el-tag :type="getFileTagType(currentDocument?.type || '')">{{ currentDocument?.type?.toUpperCase() }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件大小" label-width="100px">{{ formatFileSize(currentDocument?.size || 0) }}</el-descriptions-item>
          <el-descriptions-item label="分块数量" label-width="100px">
            <el-tag type="primary">{{ currentDocument?.chunkCount }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="处理状态" label-width="100px">
            <div class="status-info">
              <el-icon v-if="currentDocument?.status === 'processing'" :size="16" class="status-icon loading-icon"><Loading /></el-icon>
              <el-icon v-else :size="16" class="status-icon success-icon"><CircleCheck /></el-icon>
              <el-tag :type="currentDocument?.status === 'processed' || currentDocument?.status === 'READY' ? 'success' : 'warning'">
                {{ currentDocument?.status === 'processed' || currentDocument?.status === 'READY' ? '已处理' : '处理中' }}
              </el-tag>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" label-width="100px">{{ formatDate(currentDocument?.createdAt || '') }}</el-descriptions-item>
        </el-descriptions>

        <div class="chunks-section">
          <h4 class="section-title">
            <el-icon :size="18"><DocumentIcon /></el-icon>
            <span>分块预览</span>
            <el-badge :value="documentChunks.length" class="chunks-badge" />
          </h4>
          
          <el-collapse v-loading="loadingChunks" class="chunks-collapse">
            <el-collapse-item
              v-for="chunk in documentChunks"
              :key="chunk.id"
              :title="`分块 ${chunk.chunkIndex + 1}（${chunk.content.length} 字符）`"
            >
              <div class="chunk-content">
                <pre class="chunk-text">{{ chunk.content }}</pre>
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <div v-if="documentChunks.length === 0 && !loadingChunks" class="empty-chunks">
            <el-icon :size="48" class="empty-icon"><QuestionFilled /></el-icon>
            <p>暂无分块数据</p>
            <p class="empty-hint">文档可能还在处理中或内容为空</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile, UploadInstance } from 'element-plus'
import {
  Upload, Top, Document as DocumentIcon, Search, View,
  Loading, CircleCheck, QuestionFilled, FolderOpened, DeleteFilled
} from '@element-plus/icons-vue'
import { knowledgeApi } from '@/api'
import type { Document, DocumentDetail, DocumentChunk } from '@/types'

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const documentName = ref('')
const uploading = ref(false)
const processingDocId = ref<string | null>(null)  // waiting for background parse

const documents = ref<Document[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchKeyword = ref('')
const searchType = ref('')

const detailDialogVisible = ref(false)
const currentDocument = ref<DocumentDetail | null>(null)
const documentChunks = ref<DocumentChunk[]>([])
const loadingChunks = ref(false)

// ── 轮询 ──
let pollTimer: ReturnType<typeof setInterval> | null = null

const startPolling = (docId: string) => {
  processingDocId.value = docId
  pollTimer = setInterval(async () => {
    try {
      const doc = await knowledgeApi.getDocument(docId)
      if (doc.status === 'READY' || doc.status === 'ERROR') {
        if (pollTimer) clearInterval(pollTimer)
        pollTimer = null
        processingDocId.value = null
        loadDocuments()
        if (doc.status === 'READY') {
          ElMessage.success(`文档「${doc.name}」处理完成，共 ${doc.chunkCount} 个分块`)
        } else if (doc.status === 'ERROR') {
          ElMessage.error(`文档处理失败`)
        }
      }
    } catch {
      // 继续轮询
    }
  }, 1500)
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 文件选择处理
const handleFileChange = (file: UploadFile) => {
  selectedFile.value = file.raw as File
}

// 超出限制处理
const handleExceed = () => {
  ElMessage.warning('最多只能上传一个文件')
}

// 上传文档
const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  try {
    const doc = await knowledgeApi.uploadDocument(selectedFile.value, documentName.value)
    ElMessage.success('上传成功，正在处理中...')
    selectedFile.value = null
    documentName.value = ''
    uploadRef.value?.clearFiles()
    // 开始轮询状态
    startPolling(doc.id)
    // 立即显示在列表中（状态为 processing）
    loadDocuments()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 加载文档列表
const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await knowledgeApi.getDocuments(
      currentPage.value,
      pageSize.value,
      searchKeyword.value,
      searchType.value
    )
    documents.value = response.list
    total.value = response.total
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadDocuments()
}

// 分页变化
const handlePageChange = () => {
  loadDocuments()
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadDocuments()
}

// 查看详情
const handleViewDetail = async (doc: Document) => {
  try {
    currentDocument.value = await knowledgeApi.getDocument(doc.id)
    loadingChunks.value = true
    documentChunks.value = await knowledgeApi.getDocumentChunks(doc.id)
    loadingChunks.value = false
    detailDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '获取详情失败')
  }
}

// 删除文档
const handleDelete = async (doc: Document) => {
  try {
    await ElMessageBox.confirm('确定要删除该文档吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await knowledgeApi.deleteDocument(doc.id)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

// 格式化文件大小
const formatFileSize = (size: number): string => {
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
  return (size / (1024 * 1024)).toFixed(2) + ' MB'
}

// 格式化日期
const formatDate = (date: string): string => {
  return new Date(date).toLocaleString('zh-CN')
}

// 获取文件图标
const getFileIcon = (type: string) => {
  const iconMap: Record<string, any> = {
    'pdf': DocumentIcon,
    'docx': DocumentIcon,
    'txt': DocumentIcon,
    'md': DocumentIcon
  }
  return iconMap[type] || DocumentIcon
}

// 获取文件标签类型
const getFileTagType = (type: string): string => {
  const typeMap: Record<string, string> = {
    'pdf': 'danger',
    'docx': 'primary',
    'txt': 'success',
    'md': 'warning'
  }
  return typeMap[type] || 'info'
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.knowledge-page {
  display: flex;
  gap: 20px;
  height: calc(100vh - 48px);
}

.upload-card {
  width: 400px;
  flex-shrink: 0;
}

.list-card {
  flex: 1;
  overflow: hidden;
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

.icon-purple {
  color: #8b5cf6;
}

.icon-blue {
  color: #3b82f6;
}

.badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.search-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 200px;
}

.type-select {
  width: 110px;
}

.search-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.upload-section {
  padding: 16px;
}

.upload-area {
  border: 2px dashed #e0e3e8;
  border-radius: 14px;
  padding: 36px 20px;
  transition: all .2s ease;
}

.upload-area:hover {
  border-color: var(--c-primary);
  background: rgba(99, 102, 241, .03);
}

.upload-icon-wrapper {
  width: 72px;
  height: 72px;
  background: rgba(99, 102, 241, .08);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
}

.upload-icon {
  color: var(--c-primary);
}

.upload-text {
  text-align: center;
}

.upload-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
  margin: 0 0 6px 0;
}

.upload-subtitle {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0;
}

.upload-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
  font-size: 12px;
  color: var(--c-text-secondary);
}

.selected-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(99, 102, 241, .04);
  border-radius: 8px;
  margin: 14px 0;
}

.file-icon {
  color: var(--c-primary);
}

.file-name {
  font-weight: 500;
  color: var(--c-text);
  font-size: 13px;
}

.file-size {
  color: var(--c-text-secondary);
  font-size: 12px;
}

.document-name-input {
  margin-bottom: 14px;
}

.upload-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  font-size: 14px;
  font-weight: 500;
}

.document-table {
  margin-top: 8px;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-type-icon {
  color: var(--c-primary);
}

.file-name-text {
  font-weight: 500;
  color: var(--c-text);
}

.file-size-text {
  color: var(--c-text-secondary);
  font-size: 12px;
}

.chunk-tag {
  background: rgba(99, 102, 241, .08);
  color: var(--c-primary);
  border: none;
}

.status-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  font-size: 14px;
}

.loading-icon {
  color: #f59e0b;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.success-icon {
  color: #10b981;
}

.status-text {
  font-size: 12px;
}

.status-text.processing {
  color: #f59e0b;
}

.status-text.READY,
.status-text.processed {
  color: #10b981;
}

.date-text {
  color: var(--c-text-secondary);
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.view-btn:hover {
  color: var(--c-primary);
}

.delete-btn:hover {
  color: #ef4444;
}

.pagination {
  padding: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail-dialog {
  border-radius: var(--radius);
}

.detail-content {
  padding: 8px;
}

.document-info {
  margin-bottom: 20px;
}

.info-icon-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  color: var(--c-primary);
}

.status-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunks-section {
  margin-top: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
  margin-bottom: 14px;
}

.chunks-badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.chunks-collapse {
  background: transparent;
}

.chunk-content {
  background: #f9fafb;
  border-radius: 8px;
  padding: 14px;
}

.chunk-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.empty-chunks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #c0c4cc;
}

.empty-icon {
  margin-bottom: 12px;
  color: #d1d5db;
}

.empty-hint {
  font-size: 12px;
  margin-top: 4px;
}
</style>