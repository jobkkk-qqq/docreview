<template>
  <div class="system-settings">
    <el-card shadow="never">
      <template #header>
        <span>系统配置</span>
      </template>

      <el-form
        ref="settingsFormRef"
        :model="settingsForm"
        :rules="settingsRules"
        label-width="140px"
        style="max-width: 700px"
        v-loading="loading"
      >
        <!-- 系统名称（公司名） -->
        <el-form-item label="系统名称" prop="brand_name">
          <el-input
            v-model="settingsForm.brand_name"
            placeholder="请输入系统名称（公司名）"
            maxlength="30"
          />
          <div class="form-tip">显示在登录页和系统左上角的名称，可修改为使用该系统的公司名称</div>
        </el-form-item>

        <!-- 文档存储路径 -->
        <el-form-item label="文档存储路径" prop="storage_path">
          <el-input
            v-model="settingsForm.storage_path"
            placeholder="请输入文档存储的根目录路径"
          >
            <template #append>
              <el-button @click="handleBrowseFolder">浏览</el-button>
            </template>
          </el-input>
          <div class="form-tip">设置文档文件的物理存储路径，需要服务端有写入权限</div>
        </el-form-item>

        <!-- 单文件大小限制 -->
        <el-form-item label="单文件大小限制" prop="max_file_size">
          <el-input-number
            v-model="settingsForm.max_file_size"
            :min="1"
            :max="500"
            :step="1"
          />
          <span class="input-suffix">MB</span>
          <div class="form-tip">单个文档文件允许的最大上传大小</div>
        </el-form-item>

        <!-- 文件类型白名单 -->
        <el-form-item label="文件类型白名单" prop="allowed_file_types">
          <el-select
            v-model="settingsForm.allowed_file_types"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择文件类型"
            style="width: 100%"
          >
            <el-option
              v-for="ft in commonFileTypes"
              :key="ft"
              :label="ft"
              :value="ft"
            />
          </el-select>
          <div class="form-tip">允许上传的文件扩展名列表，可手动输入添加</div>
        </el-form-item>

        <!-- 水印设置 -->
        <el-form-item label="启用水印">
          <el-switch v-model="settingsForm.watermark_enabled" />
        </el-form-item>

        <el-form-item label="水印文字" v-if="settingsForm.watermark_enabled">
          <el-input v-model="settingsForm.watermark_text" placeholder="请输入水印文字" />
        </el-form-item>

        <!-- 自动审核 -->
        <el-form-item label="自动审核">
          <el-switch v-model="settingsForm.auto_review" />
          <span class="switch-tip">开启后，上传的公开文档将自动通过审核</span>
        </el-form-item>

        <!-- 保存按钮 -->
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          <el-button @click="handleReset">恢复默认</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 文档恢复管理（仅管理员可见） -->
    <el-card v-if="isSuperuser" shadow="never" style="margin-top: 24px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span>文档恢复</span>
          <el-button size="small" @click="fetchDeletedDocs" :loading="deletedLoading">刷新</el-button>
        </div>
      </template>

      <div style="margin-bottom:16px;font-size:13px;color:#909399">
        显示已删除的文档，可搜索并恢复。恢复后文档将移回原目录，并还原访问权限。
      </div>

      <!-- 搜索栏 -->
      <div style="display:flex;gap:12px;margin-bottom:16px">
        <el-input
          v-model="deletedKeyword"
          placeholder="搜索标题或文档编号"
          clearable
          style="max-width: 360px"
          @keyup.enter="handleDeletedSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleDeletedSearch">搜索</el-button>
      </div>

      <!-- 已删除文档列表 -->
      <el-table
        :data="deletedDocs"
        v-loading="deletedLoading"
        border
        stripe
        size="small"
        style="width: 100%"
        max-height="480"
      >
        <el-table-column prop="doc_no" label="文档编号" width="160" />
        <el-table-column prop="title" label="文档标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            {{ row.category?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="上传者" width="120">
          <template #default="{ row }">
            {{ row.uploader?.display_name || row.uploader?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" width="180" show-overflow-tooltip />
        <el-table-column label="删除时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.deleted_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              @click="handleRestore(row)"
              :loading="restoringId === row.id"
            >恢复</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!deletedLoading && deletedDocs.length === 0" description="暂无已删除的文档" :image-size="80" />

      <!-- 分页 -->
      <div v-if="deletedTotal > 0" style="display:flex;justify-content:flex-end;margin-top:16px">
        <el-pagination
          v-model:current-page="deletedPage"
          :page-size="deletedPageSize"
          :total="deletedTotal"
          layout="total, prev, pager, next"
          small
          @current-change="fetchDeletedDocs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
/**
 * 系统配置页面
 * 包含文档存储路径、文件大小限制、文件类型白名单等系统级配置
 * 以及文档恢复管理（仅管理员）
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getSystemSettings, updateSystemSettings } from '../api/system.js'
import { getDeletedDocuments, restoreDocument } from '../api/document.js'
import { setBrandName } from '../utils/brand.js'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const settingsFormRef = ref(null)

// 是否是超级管理员
const isSuperuser = computed(() => authStore.userInfo?.is_superuser === true)

// 常见文件类型
const commonFileTypes = [
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.txt',
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.bmp',
  '.zip',
  '.rar',
  '.7z',
  '.csv'
]

// 默认配置
const defaultSettings = {
  brand_name: 'XXX数字档案管理系统',
  storage_path: '',
  max_file_size: 50,
  allowed_file_types: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'],
  watermark_enabled: false,
  watermark_text: '',
  auto_review: false
}

// 配置表单
const settingsForm = reactive({ ...defaultSettings })

// 校验规则
const settingsRules = {
  storage_path: [
    { required: true, message: '请输入文档存储路径', trigger: 'blur' }
  ],
  max_file_size: [
    { required: true, message: '请设置文件大小限制', trigger: 'blur' }
  ],
  allowed_file_types: [
    {
      type: 'array',
      required: true,
      message: '请至少选择一种文件类型',
      trigger: 'change'
    }
  ]
}

// ── 文档恢复 ──────────────────────────────────────────
const deletedKeyword = ref('')
const deletedDocs = ref([])
const deletedTotal = ref(0)
const deletedPage = ref(1)
const deletedPageSize = ref(20)
const deletedLoading = ref(false)
const restoringId = ref(null)

/**
 * 格式化时间
 */
function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * 加载已删除文档列表
 */
async function fetchDeletedDocs() {
  deletedLoading.value = true
  try {
    const res = await getDeletedDocuments({
      page: deletedPage.value,
      page_size: deletedPageSize.value,
      keyword: deletedKeyword.value || undefined,
    })
    deletedDocs.value = res.items || []
    deletedTotal.value = res.total || 0
  } catch {
    // 错误已在拦截器中处理
  } finally {
    deletedLoading.value = false
  }
}

/**
 * 搜索已删除文档
 */
function handleDeletedSearch() {
  deletedPage.value = 1
  fetchDeletedDocs()
}

/**
 * 恢复文档
 */
async function handleRestore(row) {
  try {
    await ElMessageBox.confirm(
      `确定要恢复文档「${row.title}」吗？恢复后文件将移回原目录。`,
      '恢复确认',
      { confirmButtonText: '确定恢复', cancelButtonText: '取消', type: 'info' }
    )
    restoringId.value = row.id
    await restoreDocument(row.id)
    ElMessage.success('文档恢复成功')
    fetchDeletedDocs()
  } catch {
    // 取消或错误
  } finally {
    restoringId.value = null
  }
}

/**
 * 加载系统配置
 */
async function fetchSettings() {
  loading.value = true
  try {
    const res = await getSystemSettings()
    if (res && typeof res === 'object') {
      Object.assign(settingsForm, {
        brand_name: res.brand_name || defaultSettings.brand_name,
        storage_path: res.storage_path || '',
        max_file_size: parseInt(res.max_file_size) || 50,
        allowed_file_types: res.allowed_file_types ? JSON.parse(res.allowed_file_types) : defaultSettings.allowed_file_types,
        watermark_enabled: res.watermark_enabled === 'true',
        watermark_text: res.watermark_text || '',
        auto_review: res.auto_review === 'true'
      })
      setBrandName(settingsForm.brand_name)
    }
  } catch (error) {
    // 首次加载可能没有配置，使用默认值
  } finally {
    loading.value = false
  }
}

/**
 * 保存配置
 */
async function handleSave() {
  if (!settingsFormRef.value) return
  await settingsFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const submitData = {
        brand_name: settingsForm.brand_name,
        storage_path: settingsForm.storage_path,
        max_file_size: String(settingsForm.max_file_size),
        allowed_file_types: JSON.stringify(settingsForm.allowed_file_types),
        watermark_enabled: String(settingsForm.watermark_enabled),
        watermark_text: settingsForm.watermark_text,
        auto_review: String(settingsForm.auto_review)
      }
      await updateSystemSettings(submitData)
      setBrandName(settingsForm.brand_name)
      ElMessage.success('配置保存成功')
    } catch (error) {
      // 错误已在拦截器中处理
    } finally {
      saving.value = false
    }
  })
}

/**
 * 恢复默认配置
 */
function handleReset() {
  Object.assign(settingsForm, { ...defaultSettings })
}

/**
 * 浏览文件夹（前端模拟，实际路径需要服务端支持）
 */
function handleBrowseFolder() {
  // 浏览器安全限制，无法直接选择文件夹路径
  // 这里提示用户手动输入路径
  ElMessage.info('请手动输入服务器上的文档存储绝对路径')
}

onMounted(() => {
  fetchSettings()
  if (isSuperuser.value) {
    fetchDeletedDocs()
  }
})
</script>

<style scoped>
.system-settings {
  max-width: 900px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 4px;
}

.input-suffix {
  margin-left: 8px;
  color: #606266;
}

.switch-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
