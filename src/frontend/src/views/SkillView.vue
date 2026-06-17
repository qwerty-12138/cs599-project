<template>
  <div class="skill-page">
    <el-card class="skill-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="20" class="icon-purple"><MagicStick /></el-icon>
            <span class="header-title">Skill 管理</span>
          </div>
          <div class="header-actions">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleImportFile"
              accept=".md,.txt"
            >
              <el-button size="small">
                <el-icon :size="16"><Upload /></el-icon>导入 Markdown
              </el-button>
            </el-upload>
            <el-button type="primary" size="small" @click="handleCreate">
              <el-icon :size="16"><Plus /></el-icon>新建 Skill
            </el-button>
          </div>
        </div>
      </template>

      <div class="search-area">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索 Skill 名称..."
          clearable
          class="search-input"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="searchCategory" placeholder="分类筛选" clearable class="category-select" @change="handleSearch">
          <el-option label="系统提示" value="system" />
          <el-option label="角色扮演" value="roleplay" />
          <el-option label="代码辅助" value="coding" />
          <el-option label="写作" value="writing" />
          <el-option label="导入" value="imported" />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <el-table :data="skills" v-loading="loading" stripe empty-text="暂无 Skill">
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => handleToggle(row, v)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name-icon">{{ row.icon || '🧠' }}</span>
              <span class="name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag :type="row.category === 'system' ? 'primary' : row.category === 'roleplay' ? 'warning' : row.category === 'coding' ? 'success' : 'info'" size="small">{{ row.category || '未分类' }}</el-tag>
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
        @size-change="loadSkills"
        @current-change="loadSkills"
        class="pagination"
      />
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingSkill ? '编辑 Skill' : '新建 Skill'" width="700px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="Skill 名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="简短描述该 Skill 的功能" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="选择分类" style="width:100%">
            <el-option label="系统提示" value="system" />
            <el-option label="角色扮演" value="roleplay" />
            <el-option label="代码辅助" value="coding" />
            <el-option label="写作" value="writing" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="emoji 图标，如 🧠" maxlength={10} />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="form.content" type="textarea" :rows="12" placeholder="Skill 的系统提示词内容（Markdown 格式）" />
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
import { MagicStick, Plus, Upload } from '@element-plus/icons-vue'
import { skillApi } from '@/api'
import type { Skill } from '@/types'

const skills = ref<Skill[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const searchCategory = ref('')

const dialogVisible = ref(false)
const editingSkill = ref<Skill | null>(null)
const saving = ref(false)

const form = ref({ name: '', description: '', content: '', category: '', icon: '' })

const loadSkills = async () => {
  loading.value = true
  try {
    const res = await skillApi.getSkills(currentPage.value, pageSize.value, searchKeyword.value, searchCategory.value)
    skills.value = res.list
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadSkills()
}

const handleCreate = () => {
  editingSkill.value = null
  form.value = { name: '', description: '', content: '', category: '', icon: '' }
  dialogVisible.value = true
}

const handleEdit = (skill: Skill) => {
  editingSkill.value = skill
  form.value = { name: skill.name, description: skill.description || '', content: skill.content, category: skill.category || '', icon: skill.icon || '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name || !form.value.content) {
    ElMessage.warning('名称和内容不能为空')
    return
  }
  saving.value = true
  try {
    if (editingSkill.value) {
      await skillApi.updateSkill(editingSkill.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await skillApi.createSkill(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadSkills()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleToggle = async (skill: Skill, enabled: boolean) => {
  try {
    await skillApi.updateSkill(skill.id, { enabled })
    skill.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (skill: Skill) => {
  try {
    await ElMessageBox.confirm('确定删除此 Skill？', '提示', { type: 'warning' })
    await skillApi.deleteSkill(skill.id)
    ElMessage.success('删除成功')
    loadSkills()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

const handleImportFile = async (uploadFile: any) => {
  try {
    await skillApi.importSkill(uploadFile.raw)
    ElMessage.success('导入成功')
    loadSkills()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '导入失败')
  }
}

const formatDate = (date: string) => new Date(date).toLocaleString('zh-CN')

onMounted(loadSkills)
</script>

<style scoped>
.skill-page { height: calc(100vh - 48px); }
.skill-card { height: 100%; display: flex; flex-direction: column; }
.skill-card :deep(.el-card__body) { flex: 1; overflow: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-title { font-size: 15px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }
.icon-purple { color: #8b5cf6; }
.search-area { display: flex; gap: 8px; margin-bottom: 16px; }
.search-input { width: 240px; }
.category-select { width: 140px; }
.name-cell { display: flex; align-items: center; gap: 6px; }
.name-icon { font-size: 18px; }
.name-text { font-weight: 500; }
.pagination { padding: 16px 0 0; display: flex; justify-content: flex-end; }
</style>
