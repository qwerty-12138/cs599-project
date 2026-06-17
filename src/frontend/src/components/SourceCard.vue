<template>
  <div class="source-card">
    <div class="source-header">
      <el-tag size="small" :type="tagType" class="source-tag">
        <el-icon :size="12"><Document /></el-icon>
        {{ source.documentName || '未知文档' }}
      </el-tag>
      <span class="source-score" v-if="source.score">
        {{ (source.score * 100).toFixed(0) }}%
      </span>
    </div>
    <div class="source-content">{{ source.content }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'
import type { Source } from '@/types'

const props = defineProps<{ source: Source }>()

const tagType = computed(() => {
  if (!props.source.score) return 'info'
  if (props.source.score >= 0.8) return 'success'
  if (props.source.score >= 0.6) return 'warning'
  return 'danger'
})
</script>

<style scoped>
.source-card {
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
  gap: 8px;
}
.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-score {
  font-size: 11px;
  color: var(--c-primary, #6366f1);
  font-weight: 500;
  flex-shrink: 0;
}
.source-content {
  font-size: 12px;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 120px;
  overflow-y: auto;
  padding-right: 8px;
  line-height: 1.5;
}
</style>
