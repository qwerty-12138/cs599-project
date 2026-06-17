<template>
  <div class="app-layout">
    <!-- 左侧导航栏 -->
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="logo-mark">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#logo-grad)" />
            <path d="M10 16L14 20L22 12" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="logo-grad" x1="0" y1="0" x2="32" y2="32">
                <stop stop-color="#6366f1"/>
                <stop offset="1" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span class="logo-label">RAG Assistant</span>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/chat" class="nav-item" :class="{ active: route.path === '/chat' }">
          <div class="nav-icon">
            <el-icon :size="20"><ChatDotRound /></el-icon>
          </div>
          <span class="nav-label">智能问答</span>
          <div class="nav-indicator" />
        </router-link>
        <router-link to="/knowledge" class="nav-item" :class="{ active: route.path === '/knowledge' }">
          <div class="nav-icon">
            <el-icon :size="20"><FolderOpened /></el-icon>
          </div>
          <span class="nav-label">知识库</span>
          <div class="nav-indicator" />
        </router-link>
        <router-link to="/skills" class="nav-item" :class="{ active: route.path === '/skills' }">
          <div class="nav-icon">
            <el-icon :size="20"><MagicStick /></el-icon>
          </div>
          <span class="nav-label">Skills</span>
          <div class="nav-indicator" />
        </router-link>
        <router-link to="/mcp" class="nav-item" :class="{ active: route.path === '/mcp' }">
          <div class="nav-icon">
            <el-icon :size="20"><Connection /></el-icon>
          </div>
          <span class="nav-label">MCP</span>
          <div class="nav-indicator" />
        </router-link>
        <router-link to="/tools" class="nav-item" :class="{ active: route.path === '/tools' }">
          <div class="nav-icon">
            <el-icon :size="20"><Tools /></el-icon>
          </div>
          <span class="nav-label">工具</span>
          <div class="nav-indicator" />
        </router-link>
      </nav>

      <div class="sidebar-bottom">
        <div class="version-tag">v1.0</div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { FolderOpened, ChatDotRound, MagicStick, Connection, Tools } from '@element-plus/icons-vue'

const route = useRoute()
</script>

<style>
/* ===== Reset & Base ===== */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --sidebar-w: 72px;
  --c-primary: #6366f1;
  --c-primary-light: #818cf8;
  --c-bg: #f8f9fc;
  --c-surface: #ffffff;
  --c-border: #e8eaef;
  --c-text: #1e1e2e;
  --c-text-secondary: #6b7280;
  --radius: 12px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.06);
  --shadow-md: 0 4px 24px rgba(0,0,0,.07);
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html, body {
  height: 100%;
  font-family: var(--font);
  background: var(--c-bg);
  color: var(--c-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}

/* ===== Layout ===== */
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ===== Sidebar ===== */
.sidebar {
  width: var(--sidebar-w);
  height: 100vh;
  background: var(--c-surface);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  flex-shrink: 0;
  z-index: 100;
}

.sidebar-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 32px;
}

.logo-mark {
  width: 36px;
  height: 36px;
  cursor: pointer;
  transition: transform .2s;
}
.logo-mark:hover {
  transform: scale(1.08);
}
.logo-mark svg {
  width: 100%;
  height: 100%;
}

.logo-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--c-text-secondary);
  letter-spacing: .04em;
  text-transform: uppercase;
}

/* ===== Nav ===== */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 52px;
  padding: 10px 0;
  border-radius: 12px;
  text-decoration: none;
  color: var(--c-text-secondary);
  transition: all .2s ease;
  cursor: pointer;
}

.nav-item:hover {
  color: var(--c-primary);
  background: rgba(99, 102, 241, .06);
}

.nav-item.active {
  color: var(--c-primary);
  background: rgba(99, 102, 241, .1);
}

.nav-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
}

.nav-indicator {
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 3px 3px 0;
  background: var(--c-primary);
  transition: height .25s ease;
}

.nav-item.active .nav-indicator {
  height: 24px;
}

/* ===== Sidebar bottom ===== */
.sidebar-bottom {
  display: flex;
  align-items: center;
  justify-content: center;
}

.version-tag {
  font-size: 10px;
  color: #c0c4cc;
  font-weight: 500;
}

/* ===== Main ===== */
.main-content {
  flex: 1;
  overflow: auto;
  background: var(--c-bg);
  padding: 24px 28px;
}

/* ===== Page transition ===== */
.page-enter-active,
.page-leave-active {
  transition: opacity .25s ease, transform .25s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ===== Element Plus Overrides ===== */
.el-card {
  border-radius: var(--radius);
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  background: var(--c-surface);
}

.el-card__header {
  border-bottom: 1px solid var(--c-border);
  padding: 14px 20px;
  background: transparent;
}

.el-button--primary {
  background: var(--c-primary);
  border: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all .2s ease;
}
.el-button--primary:hover {
  background: var(--c-primary-light);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99,102,241,.3);
}

.el-button--danger {
  border-radius: 8px;
}

.el-tag {
  border-radius: 6px;
}

.el-input__wrapper {
  border-radius: 8px;
}

.el-textarea__inner {
  border-radius: 8px;
}

.el-table {
  --el-table-row-hover-bg-color: rgba(99,102,241,.04);
}
.el-table th {
  background: #fafbfd;
  font-weight: 600;
}

.el-dialog {
  border-radius: var(--radius);
}

.el-collapse-item__header {
  border-radius: 8px;
  margin-bottom: 6px;
}

.el-pagination {
  padding: 16px;
}
</style>