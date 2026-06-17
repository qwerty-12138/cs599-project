<template>
  <div class="loading-spinner" :style="{ height: height }">
    <el-icon :size="size" class="spinner-icon"><Loading /></el-icon>
    <span v-if="text" class="spinner-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  text?: string
  size?: number
  height?: string
}>(), {
  text: '',
  size: 32,
  height: '200px'
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.spinner-icon {
  color: var(--c-primary, #6366f1);
  animation: loading-rotate 1s linear infinite;
}
@keyframes loading-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spinner-text {
  font-size: 13px;
  color: #9ca3af;
}
</style>
