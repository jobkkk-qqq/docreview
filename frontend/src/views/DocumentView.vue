<template>
  <div class="document-view page-container">
    <!-- 搜索栏（简化版，适合普通用户） -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item>
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索文档..."
            clearable
            style="width: 300px"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="分类">
          <el-select
            v-model="searchForm.category_id"
            placeholder="全部分类"
            clearable
            style="width: 160px"
          >
            <el-option
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 文档列表 -->
    <el-card shadow="never">
      <template #header>
        <span>可查看文档</span>
      </template>

      <el-table v-loading="loading" :data="documentList" border stripe style="width: 100%">
        <el-table-column prop="doc_no" label="文档编号" width="130" show-overflow-tooltip />
        <el-table-column prop="title" label="文档标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="文件类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="fileTypeTagType(row.file_name)">
              {{ (row.file_name||'?').split('.').pop()?.toUpperCase() || '?' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            {{ row.category?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="保密等级" width="100">
          <template #default="{ row }">
            <el-tag
              :type="confidentialityTagType(row.confidential_level)"
              size="small"
            >
              {{ confidentialityLabel(row.confidential_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传人" width="100">
          <template #default="{ row }">
            {{ row.uploader?.display_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="table-op-btns">
            <el-button type="primary" link size="small" @click="handleView(row)">
              查看详情
            </el-button>
            <el-button
              v-if="isPreviewable(row.file_name)"
              type="primary"
              link
              size="small"
              @click="handlePreview(row)"
            >
              预览
            </el-button>
            <el-button type="success" link size="small" @click="handleDownload(row)">
              下载
            </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 文档详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="文档详情"
      width="650px"
      destroy-on-close
    >
      <el-descriptions :column="2" border v-if="currentDoc">
        <el-descriptions-item label="文档编号" :span="2">
          {{ currentDoc.doc_no }}
        </el-descriptions-item>
        <el-descriptions-item label="文档标题" :span="2">
          {{ currentDoc.title }}
        </el-descriptions-item>
        <el-descriptions-item label="分类">
          {{ currentDoc.category?.name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="保密等级">
          <el-tag
            :type="confidentialityTagType(currentDoc.confidential_level)"
            size="small"
          >
            {{ confidentialityLabel(currentDoc.confidential_level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="上传人">
          {{ currentDoc.uploader?.display_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="上传时间">
          {{ formatDate(currentDoc.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="文件大小">
          {{ formatFileSize(currentDoc.file_size) }}
        </el-descriptions-item>
        <el-descriptions-item label="文件格式">
          {{ currentDoc.file_type }}
        </el-descriptions-item>
        <el-descriptions-item label="文档描述" :span="2">
          {{ currentDoc.summary || '无' }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="success" @click="handleDownload(currentDoc)">下载文档</el-button>
      </template>
    </el-dialog>

    <!-- 文档预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="文档预览"
      fullscreen
      destroy-on-close
      draggable
    >
      <div v-if="previewLoading" class="preview-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="previewError" class="preview-error">
        <el-result icon="error" title="预览加载失败" sub-title="请稍后重试或下载后查看">
          <template #extra>
            <el-button type="primary" @click="handleDownloadFromPreview">下载查看</el-button>
          </template>
        </el-result>
      </div>
      <div v-else-if="previewUnsupported" class="preview-unsupported">
        <el-result icon="warning" :title="previewErrorTitle" :sub-title="previewErrorMessage">
          <template #extra>
            <el-button type="primary" @click="handleDownloadFromPreview">下载查看</el-button>
          </template>
        </el-result>
      </div>
      <embed
        v-else-if="previewUrl && previewType === 'pdf'"
        :src="previewUrl"
        class="preview-iframe"
        type="application/pdf"
      />
      <div v-else-if="previewUrl && previewType === 'txt'" class="preview-txt">
        <pre>{{ previewText }}</pre>
      </div>
      <div v-else-if="previewUrl && previewType === 'image'" class="preview-image">
        <img :src="previewUrl" class="preview-img" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 文档查看页面
 * 普通用户使用的简化版文档查看界面，提供搜索、查看详情、预览、下载功能
 */
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getDocumentList, getDocumentDetail, downloadDocument, reportPreviewLog } from '../api/document.js'
import { getCategoryListSimple } from '../api/category.js'
import { isPreviewable, getPreviewType, OFFICE_EXTS, IMAGE_MIME_MAP } from '../utils/preview.js'
import { saveBlobAsFile } from '../utils/download.js'
import { formatDate, formatFileSize, fileTypeTagType, confidentialityTagType, confidentialityLabel } from '../utils/format.js'
import { useMobile } from '../composables/useMobile.js'
import request from '../api/request.js'

const route = useRoute()

// 移动端检测（使用公共 composable，避免内存泄漏）
const { isMobile } = useMobile()

const loading = ref(false)
const documentList = ref([])
const categoryOptions = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const searchForm = reactive({
  keyword: '',
  category_id: ''
})

const detailVisible = ref(false)
const currentDoc = ref(null)

// 预览对话框
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewUrl = ref('')
const previewType = ref('')
const previewText = ref('')
const previewError = ref(false)
const previewUnsupported = ref(false)
const previewDownloadRow = ref(null)
const previewErrorTitle = ref('无法预览')
const previewErrorMessage = ref('该文件格式暂不支持在线预览，请下载后查看')

async function fetchDocuments() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      category_id: searchForm.category_id || undefined
    }
    const res = await getDocumentList(params)
    documentList.value = res.items || res.data || []
    pagination.total = res.total || 0
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function fetchCategories() {
  try {
    // 统一使用 getCategoryListSimple 获取全量分类
    const res = await getCategoryListSimple()
    categoryOptions.value = res.items || res.data || res || []
  } catch {
    // 错误已在拦截器中处理
  }
}

function handleSearch() {
  pagination.page = 1
  fetchDocuments()
}

function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchDocuments()
}

function handlePageChange(page) {
  pagination.page = page
  fetchDocuments()
}

async function handleView(row) {
  try {
    const res = await getDocumentDetail(row.id)
    currentDoc.value = res
    detailVisible.value = true
  } catch {
    // 错误已在拦截器中处理
  }
}

async function handleDownload(row) {
  if (!row) return
  try {
    const res = await downloadDocument(row.id)
    const blob = res instanceof Blob ? res : new Blob([res])
    saveBlobAsFile(blob, row.file_name || row.title || '文档')
    ElMessage.success('下载成功')
  } catch {
    // 错误已在拦截器中处理
  }
}

/**
 * 从Blob错误响应中解析错误消息
 */
async function parseBlobError(blob) {
  try {
    if (blob instanceof Blob && blob.type && blob.type.includes('application/json')) {
      const text = await blob.text()
      const data = JSON.parse(text)
      return data.detail || data.message || '预览失败'
    }
  } catch {}
  return '预览失败，请下载后查看'
}

/**
 * 预览文档
 */
async function handlePreview(row) {
  if (!row.file_name) {
    ElMessage.warning('文件信息不完整，无法预览')
    return
  }

  const ext = (row.file_name.split('.').pop() || '').toLowerCase()
  const type = getPreviewType(row.file_name)
  const token = localStorage.getItem('token') || ''

  // 重置预览状态
  previewErrorTitle.value = '无法预览'
  previewErrorMessage.value = '该文件格式暂不支持在线预览，请下载后查看'

  // 手机端：直接导航到 PDF/图片 URL，让手机浏览器自身阅读器渲染
  if (isMobile.value) {
    if (OFFICE_EXTS.includes(ext) || type === 'pdf') {
      window.location.href = `/api/documents/${row.id}/preview.pdf?token=${encodeURIComponent(token)}`
      return
    }
    if (type === 'image') {
      window.location.href = `/api/documents/${row.id}/download?inline=1&token=${encodeURIComponent(token)}`
      return
    }
    if (type === 'txt') {
      previewLoading.value = true
      previewError.value = false
      previewUnsupported.value = false
      previewVisible.value = true
      try {
        const res = await downloadDocument(row.id)
        previewText.value = await res.text()
        previewType.value = 'txt'
      } catch { previewError.value = true }
      finally { previewLoading.value = false }
      return
    }
    ElMessage.warning('手机端暂不支持预览该文件格式')
    return
  }

  // PC 端：内嵌预览
  previewLoading.value = true
  previewError.value = false
  previewUnsupported.value = false
  previewVisible.value = true

  try {
    if (!type) {
      previewUnsupported.value = true
      previewDownloadRow.value = row
      return
    }

    // Office 文件和 PDF 统一使用 preview-pdf 接口
    if (['word', 'excel', 'ppt', 'pdf'].includes(type)) {
      try {
        const pdfRes = await request.get(`/documents/${row.id}/preview-pdf`, { responseType: 'blob' })
        // 检查返回的是否是错误JSON
        if (pdfRes instanceof Blob && pdfRes.type && pdfRes.type.includes('application/json')) {
          const errMsg = await parseBlobError(pdfRes)
          throw new Error(errMsg)
        }
        const pdfBlob = pdfRes instanceof Blob ? pdfRes : new Blob([pdfRes], { type: 'application/pdf' })
        previewUrl.value = URL.createObjectURL(pdfBlob)
        previewType.value = 'pdf'
        // 预览成功后再上报日志
        reportPreviewLog(row.id).catch(() => {})
      } catch (err) {
        const errMsg = err?.errorMessage || err?.message || '预览失败，请下载后查看'
        previewErrorTitle.value = '无法在线预览'
        previewErrorMessage.value = errMsg
        previewUnsupported.value = true
        previewDownloadRow.value = row
      }
    } else if (type === 'txt') {
      const res = await downloadDocument(row.id)
      previewText.value = await res.text()
      const txtBlob = res instanceof Blob ? res : new Blob([res], { type: 'text/plain;charset=utf-8' })
      previewUrl.value = URL.createObjectURL(txtBlob)
      previewType.value = 'txt'
      // 预览成功后再上报日志
      reportPreviewLog(row.id).catch(() => {})
    } else if (type === 'image') {
      const res = await downloadDocument(row.id)
      const imgBlob = res instanceof Blob ? res : new Blob([res], { type: IMAGE_MIME_MAP[ext] || 'image/png' })
      previewUrl.value = URL.createObjectURL(imgBlob)
      previewType.value = 'image'
      // 预览成功后再上报日志
      reportPreviewLog(row.id).catch(() => {})
    }
  } catch (err) {
    previewError.value = true
    console.error('预览加载失败:', err)
  } finally {
    previewLoading.value = false
  }
}

/**
 * 从预览对话框下载
 */
function handleDownloadFromPreview() {
  if (previewDownloadRow.value) {
    handleDownload(previewDownloadRow.value)
  }
}

// 初始化：如果有传入关键词，自动搜索
onMounted(() => {
  const keyword = route.query.keyword
  if (keyword) {
    searchForm.keyword = keyword
  }
  fetchDocuments()
  fetchCategories()
})
</script>

<style scoped>
.document-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
