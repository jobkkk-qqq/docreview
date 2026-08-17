<template>
  <div class="operation-log">
    <!-- 搜索栏 -->
    <el-card shadow="never">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="用户">
          <el-input
            v-model="searchForm.username"
            placeholder="操作人用户名"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.action" placeholder="全部类型" clearable style="width: 140px">
            <el-option label="登录" value="login" />
            <el-option label="登出" value="logout" />
            <el-option label="上传" value="upload" />
            <el-option label="下载" value="download" />
            <el-option label="删除" value="delete" />
            <el-option label="打印" value="print" />
            <el-option label="预览" value="preview" />
            <el-option label="审核" value="review" />
            <el-option label="新增" value="create" />
            <el-option label="修改" value="update" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <el-card shadow="never">
      <template #header>
        <span>操作日志</span>
      </template>

      <el-table v-loading="loading" :data="logList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="操作人" width="100">
          <template #default="{ row }">
            {{ row.user?.display_name || row.user?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">
              {{ actionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源类型" width="100">
          <template #default="{ row }">
            {{ targetTypeLabel(row.target_type) }}
          </template>
        </el-table-column>
        <el-table-column label="资源ID" width="80">
          <template #default="{ row }">
            {{ row.target_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作详情" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatDetail(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP 地址" width="130" />
        <el-table-column prop="created_at" label="操作时间" width="170" />
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
/**
 * 操作日志页面
 * 查看系统操作记录，支持按用户、操作类型、时间范围筛选
 */
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getOperationLogs } from '../api/system.js'

const loading = ref(false)
const logList = ref([])

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const searchForm = reactive({
  username: '',
  action: '',
  dateRange: []
})

/**
 * 操作类型标签颜色
 */
function actionTagType(action) {
  const map = {
    login: 'success',
    logout: 'info',
    upload: 'primary',
    download: '',
    delete: 'danger',
    print: 'warning',
    preview: '',
    review: '',
    create: 'success',
    update: 'primary'
  }
  return map[action] || 'info'
}

/**
 * 操作类型中文标签
 */
function actionLabel(action) {
  const map = {
    login: '登录',
    logout: '登出',
    upload: '上传',
    download: '下载',
    delete: '删除',
    print: '打印',
    preview: '预览',
    review: '审核',
    create: '新增',
    update: '修改'
  }
  return map[action] || action
}

/**
 * 资源类型中文标签
 */
function targetTypeLabel(targetType) {
  const map = {
    document: '文档',
    user: '用户',
    department: '部门',
    category: '分类',
    role: '角色',
  }
  return map[targetType] || targetType || '-'
}

/**
 * 格式化操作详情
 */
function formatDetail(row) {
  if (!row.detail) return '-'
  if (typeof row.detail === 'string') {
    return row.detail
  }
  const obj = row.detail

  // 中文键名格式（如权限变更、文档批量授权等审计日志）
  if (obj['操作']) {
    const parts = []
    parts.push(obj['操作'])
    if (obj['角色']) parts.push(`角色: ${obj['角色']}`)
    if (obj['新增权限'] && obj['新增权限'].length) parts.push(`新增: ${obj['新增权限'].join('、')}`)
    if (obj['移除权限'] && obj['移除权限'].length) parts.push(`移除: ${obj['移除权限'].join('、')}`)
    if (obj['版本'] !== undefined) parts.push(`v${obj['版本']}`)
    if (obj['涉及文档数'] !== undefined) parts.push(`文档数: ${obj['涉及文档数']}`)
    return parts.join(' | ')
  }

  // 常见字段格式化
  const parts = []
  if (obj.title) parts.push(`标题: ${obj.title}`)
  if (obj.file_name) parts.push(`文件: ${obj.file_name}`)
  if (obj.name) parts.push(`名称: ${obj.name}`)
  if (obj.status) parts.push(`状态: ${obj.status}`)
  if (obj.action) parts.push(`操作: ${obj.action}`)
  if (obj.comment) parts.push(`意见: ${obj.comment}`)
  if (obj.document_id) parts.push(`文档ID: ${obj.document_id}`)
  if (obj.target_user) parts.push(`目标用户: ${obj.target_user}`)
  if (obj.is_active !== undefined) parts.push(`状态: ${obj.is_active ? '启用' : '禁用'}`)
  // 业务范围变更特殊处理
  if (obj.key === 'business_scopes' && obj.value) {
    try {
      const scopes = typeof obj.value === 'string' ? JSON.parse(obj.value) : obj.value
      if (Array.isArray(scopes)) {
        const scopeNames = scopes.map(s => s.name || s.code).join('、')
        return `业务范围：${scopeNames}（共${scopes.length}个）`
      }
    } catch (e) {
      // 解析失败，继续兜底
    }
  }
  if (parts.length > 0) return parts.join(' | ')
  // 兜底：显示人类友好的摘要
  const keys = Object.keys(obj)
  if (keys.length === 1) {
    const v = obj[keys[0]]
    return `${keys[0]}: ${v}`    // 如 document_id: 4
  }
  return JSON.stringify(obj)
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      username: searchForm.username || undefined,
      action: searchForm.action || undefined
    }
    if (searchForm.dateRange && searchForm.dateRange.length === 2) {
      params.start_date = searchForm.dateRange[0]
      params.end_date = searchForm.dateRange[1]
    }
    const res = await getOperationLogs(params)
    logList.value = res.items || res.data || []
    pagination.total = res.total || 0
  } catch (error) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchLogs()
}

function handleReset() {
  searchForm.username = ''
  searchForm.action = ''
  searchForm.dateRange = []
  pagination.page = 1
  fetchLogs()
}

function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchLogs()
}

function handlePageChange(page) {
  pagination.page = page
  fetchLogs()
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.operation-log {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
