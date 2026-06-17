import { createRouter, createWebHistory } from 'vue-router'
import Knowledge from '@/views/Knowledge.vue'
import Chat from '@/views/Chat.vue'
import SkillView from '@/views/SkillView.vue'
import McpView from '@/views/McpView.vue'

import ToolsView from '@/views/ToolsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/chat'
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: Knowledge
    },
    {
      path: '/chat',
      name: 'Chat',
      component: Chat
    },
    {
      path: '/tools',
      name: 'Tools',
      component: ToolsView
    },
    {
      path: '/skills',
      name: 'Skills',
      component: SkillView
    },
    {
      path: '/mcp',
      name: 'Mcp',
      component: McpView
    }
  ]
})

export default router
