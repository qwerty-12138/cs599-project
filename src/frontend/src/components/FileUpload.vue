<template>
  <div class="file-upload-wrapper">
    <el-upload
      ref="uploadRef"
      class="file-upload"
      drag
      :auto-upload="false"
      :limit="1"
      :accept="accept"
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
          <span>{{ acceptLabel }}</span>
          <el-tag size="small" type="warning">最大 {{ maxSizeLabel }}</el-tag>
        </div>
      </template>
    </el-upload>

    <div v-if="selectedFile" class="file-info">
      <el-icon :size="18" class="file-icon"><Document /></el-icon>
      <span class="file-name">{{ selectedFile.name }}</span>
      <span class="file-size">({{ formatSize(selectedFile.size) }})</span>
    </div>

    <slot :file="selectedFile" :clear="clearFile" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Top, Document } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance } from 'element-plus'

const props = withDefaults(defineProps<{
  accept?: string
  acceptLabel?: string
  maxSize?: number
  maxSizeLabel?: string
}>(), {
  accept: '.pdf,.docx,.txt,.md',
  acceptLabel: 'PDF、DOCX、TXT、MD',
  maxSize: 100,
  maxSizeLabel: '100MB'
})

const emit = defineEmits<{
  change: [file: File]
}>()

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)

const handleFileChange = (uploadFile: UploadFile) => {
  selectedFile.value = uploadFile.raw as File
  emit('change', uploadFile.raw as File)
}

const handleExceed = () => {
  ElMessage.warning('最多只能上传一个文件')
}

const clearFile = () => {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}

const formatSize = (size: number): string => {
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.file-upload-wrapper {
  padding: 16px;
}
.file-upload {
  border: 2px dashed #e0e3e8;
  border-radius: 14px;
  padding: 36px 20px;
  transition: all .2s ease;
}
.file-upload:hover {
  border-color: var(--c-primary, #6366f1);
  background: rgba(99, 102, 241, .03);
}
.upload-icon-wrapper {
  width: 72px; height: 72px;
  background: rgba(99, 102, 241, .08);
  border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 14px;
}
.upload-icon { color: var(--c-primary, #6366f1); }
.upload-text { text-align: center; }
.upload-title { font-size: 15px; font-weight: 600; margin: 0 0 6px; }
.upload-subtitle { font-size: 13px; color: #6b7280; margin: 0; }
.upload-tip {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 14px; font-size: 12px; color: #6b7280;
}
.file-info {
  display: flex; align-items: center; gap: 8px;
  padding: 10px; background: rgba(99,102,241,.04);
  border-radius: 8px; margin: 14px 0;
}
.file-icon { color: var(--c-primary, #6366f1); }
.file-name { font-weight: 500; font-size: 13px; }
.file-size { color: #6b7280; font-size: 12px; }
</style>
