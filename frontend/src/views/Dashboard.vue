<template>
  <div class="dashboard-container">
    <!-- 欢迎语 -->
    <div class="welcome-section">
      <h2>欢迎回来，{{ authStore.userInfo?.display_name || authStore.username || '用户' }}</h2>
      <p>今天是 {{ currentDate }}，以下是系统概况</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">文档总数</span>
              <span class="stat-value">{{ stats.total_documents || 0 }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#409eff"><Document /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">近7天新增</span>
              <span class="stat-value">{{ stats.recent_upload_count || 0 }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#67c23a"><TrendCharts /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">分类数量</span>
              <span class="stat-value">{{ stats.total_categories || 0 }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#e6a23c"><FolderOpened /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">用户数量</span>
              <span class="stat-value">{{ stats.total_users || 0 }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#f56c6c"><User /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 最近文档 -->
      <el-col :span="16">
        <el-card shadow="never" class="recent-card">
          <template #header>
            <div class="card-header">
              <span>最近上传的文档</span>
              <el-button type="primary" link @click="$router.push('/documents')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentDocs" stripe size="small">
            <el-table-column prop="doc_no" label="编号" width="120" show-overflow-tooltip />
            <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
            <el-table-column label="格式" width="70" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="fileTypeTagType(row.file_name)" effect="dark">
                  {{ fileTypeLabel(row.file_name) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分类" width="90">
              <template #default="{ row }">
                {{ row.category?.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="上传人" width="80">
              <template #default="{ row }">
                {{ row.uploader?.display_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="150" />
          </el-table>
          <el-empty v-if="recentDocs.length === 0" description="暂无文档" />
        </el-card>
      </el-col>

      <!-- 快捷搜索 -->
      <el-col :span="8">
        <el-card shadow="never" class="quick-card">
          <template #header>
            <span>快捷搜索</span>
          </template>
          <el-input
            v-model="quickKeyword"
            placeholder="输入关键词搜索文档..."
            size="large"
            clearable
            @keyup.enter="handleQuickSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleQuickSearch" />
            </template>
          </el-input>
          <div class="shortcut-links">
            <h4>常用操作</h4>
            <el-button type="primary" link @click="$router.push('/documents')">
              <el-icon><Document /></el-icon> 文档管理
            </el-button>
            <el-button type="primary" link @click="$router.push('/documents/upload')" v-if="canUpload">
              <el-icon><Upload /></el-icon> 上传文档
            </el-button>
            <el-button type="primary" link @click="$router.push('/categories')" v-if="canManageCategory">
              <el-icon><FolderOpened /></el-icon> 分类管理
            </el-button>
            <el-button type="primary" link @click="$router.push('/logs')" v-if="canViewLog">
              <el-icon><Tickets /></el-icon> 操作日志
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * 仪表盘首页
 * 展示系统统计数据、最近文档列表和快捷操作
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, TrendCharts, FolderOpened, User, Search, Upload, Tickets } from '@element-plus/icons-vue'
import { getDashboardStats, getRecentDocuments } from '../api/dashboard.js'
import { useAuthStore } from '../stores/auth.js'
import { canUploadDoc, canManageCategories, canViewAuditLogs } from '../utils/permission.js'

// 文件类型工具函数
function fileTypeLabel(fileName) {
  if (!fileName) return '-'
  return (fileName.split('.').pop()?.toUpperCase() || '-')
}
function fileTypeTagType(fileName) {
  if (!fileName) return 'info'
  const ext = fileName.split('.').pop()?.toLowerCase()
  if (['pdf'].includes(ext)) return 'danger'
  if (['doc','docx'].includes(ext)) return 'primary'
  if (['xls','xlsx','csv'].includes(ext)) return 'success'
  if (['ppt','pptx'].includes(ext)) return 'warning'
  if (['jpg','jpeg','png','gif','webp'].includes(ext)) return 'info'
  return 'info'
}

const router = useRouter()
const authStore = useAuthStore()

// 统计数据
const stats = reactive({
  total_documents: 0,
  recent_upload_count: 0,
  total_categories: 0,
  total_users: 0
})

// 最近文档
const recentDocs = ref([])

// 快捷搜索关键词
const quickKeyword = ref('')

// 当前日期
const currentDate = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  const day = now.getDate()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  const weekDay = weekDays[now.getDay()]
  return `${year}年${month}月${day}日 星期${weekDay}`
})

// 权限判断：统一基于权限码
const canUpload = computed(() => canUploadDoc())

const canManageCategory = computed(() => canManageCategories())

const canViewLog = computed(() => canViewAuditLogs())

/**
 * 加载统计数据
 */
async function fetchStats() {
  try {
    const res = await getDashboardStats()
    Object.assign(stats, res)
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

/**
 * 加载最近文档
 */
async function fetchRecentDocs() {
  try {
    const res = await getRecentDocuments({ limit: 10 })
    recentDocs.value = res.items || res.data || res || []
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

/**
 * 快捷搜索
 */
function handleQuickSearch() {
  if (quickKeyword.value.trim()) {
    router.push({ path: '/documents', query: { keyword: quickKeyword.value.trim() } })
  }
}

// 页面初始化
onMounted(() => {
  fetchStats()
  fetchRecentDocs()
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-section {
  padding: 8px 0;
}

.welcome-section h2 {
  font-size: 22px;
  color: #303133;
  margin-bottom: 4px;
}

.welcome-section p {
  font-size: 14px;
  color: #909399;
}

.stat-row {
  margin-bottom: 0;
}

.stat-card {
  border-radius: 8px;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-icon {
  opacity: 0.8;
}

.recent-card,
.quick-card {
  border-radius: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.shortcut-links {
  margin-top: 20px;
}

.shortcut-links h4 {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.shortcut-links .el-button {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
