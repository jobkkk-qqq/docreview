<template>
  <div class="document-upload">
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;align-items:center;gap:8px">
          <el-icon :size="20" color="#165dff"><UploadFilled /></el-icon>
          <span>上传文档</span>
        </div>
      </template>

      <!-- 模式切换 -->
      <el-radio-group v-model="uploadMode" style="margin-bottom:20px">
        <el-radio-button value="single">单文件上传</el-radio-button>
        <el-radio-button value="batch">批量上传</el-radio-button>
      </el-radio-group>

      <!-- ========== 单文件上传模式 ========== -->
      <div v-if="uploadMode === 'single'">
        <el-form
          ref="uploadFormRef"
          :model="uploadForm"
          :rules="uploadRules"
          label-width="100px"
          style="max-width: 700px"
        >
          <!-- 文档标题 -->
          <el-form-item label="文档标题" prop="title">
            <el-input v-model="uploadForm.title" placeholder="请输入文档标题" />
          </el-form-item>

          <!-- 文档编号 -->
          <el-form-item label="文档编号" prop="doc_no">
            <el-input v-model="uploadForm.doc_no" placeholder="不填则自动生成（年月+流水号）" />
          </el-form-item>

          <!-- 文档分类 -->
          <el-form-item label="文档分类" prop="category_id">
            <el-select v-model="uploadForm.category_id" placeholder="请选择分类" style="width: 100%">
              <el-option
                v-for="item in categoryOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              >
                <span>{{ item.name }}</span>
                <el-tag
                  v-if="isRecommendedCategory(item)"
                  size="small"
                  type="success"
                  effect="plain"
                  style="margin-left: 8px"
                >推荐</el-tag>
              </el-option>
            </el-select>
            <div v-if="isBusinessUser" class="category-filter-tip">
              已根据您的业务角色自动推荐分类，可手动切换
            </div>
          </el-form-item>

          <!-- 版本关联：作为已有文档的新版本上传 -->
          <el-form-item label="版本关联">
            <div style="width:100%">
              <div style="display:flex;align-items:center;gap:8px">
                <el-switch v-model="versionEnabled" />
                <span style="font-size:14px;color:#4e5969">作为已有文档的新版本上传</span>
                <el-tag
                  v-if="versionParentLabel"
                  size="small"
                  type="primary"
                  effect="plain"
                  closable
                  @close="clearVersionAssociation"
                >
                  关联文档：{{ versionParentLabel }}
                </el-tag>
              </div>
              <el-select
                v-if="versionEnabled"
                v-model="versionParentId"
                filterable
                remote
                :remote-method="queryDocOptions"
                :loading="docSearchLoading"
                placeholder="搜索并选择要关联为父版本的文档"
                style="width:100%;margin-top:8px"
                clearable
                @change="handleParentDocChange"
              >
                <el-option
                  v-for="doc in docSearchOptions"
                  :key="doc.id"
                  :label="doc.title"
                  :value="doc.id"
                >
                  <span>{{ doc.title }}</span>
                  <el-tag v-if="doc.version > 1" size="small" effect="plain" style="margin-left:6px">
                    v{{ doc.version }}
                  </el-tag>
                </el-option>
              </el-select>
              <div v-if="versionEnabled" style="font-size:12px;color:#86909c;line-height:22px;margin-top:2px">
                选择后：新文件将作为该文档的最新版本，继承其分类/部门/文档级别与授权角色
              </div>
            </div>
          </el-form-item>

          <!-- 部门（二级分类） -->
          <el-form-item label="所属部门" prop="department_id">
            <el-select v-model="uploadForm.department_id" placeholder="请选择部门（选填）" clearable style="width: 100%">
              <el-option
                v-for="item in departmentOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <!-- 文档级别（三级分类） -->
          <el-form-item label="文档级别" prop="doc_level">
            <el-select v-model="uploadForm.doc_level" placeholder="请选择文档级别" style="width: 100%">
              <el-option
                v-for="lv in docLevels"
                :key="lv"
                :label="lv"
                :value="lv"
              />
            </el-select>
          </el-form-item>

          <!-- 保密等级 -->
          <el-form-item label="保密等级" prop="confidential_level">
            <el-radio-group v-model="uploadForm.confidential_level">
              <el-radio value="public">公开</el-radio>
              <el-radio value="internal">内部</el-radio>
              <el-radio value="confidential">机密</el-radio>
              <el-radio value="top_secret">绝密</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 文档描述 -->
          <el-form-item label="文档描述" prop="summary">
            <el-input v-model="uploadForm.summary" type="textarea" :rows="3" placeholder="请输入文档描述（选填）" />
          </el-form-item>

          <!-- 文件上传 -->
          <el-form-item label="上传文件" prop="file">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.png,.zip,.rar"
              drag
            >
              <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 PDF、Word、Excel、PPT、TXT、图片、压缩包等格式，单文件不超过 50MB
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <!-- 同名文件提醒 -->
          <el-form-item v-if="sameNameMatches.length > 0" label="同名提醒">
            <el-alert type="warning" :closable="false" show-icon style="width:100%">
              <template #title>
                检测到 {{ sameNameMatches.length }} 个同名文档，可加入其版本管理
              </template>
              <div style="margin-top:6px;display:flex;flex-direction:column;gap:4px">
                <div
                  v-for="m in sameNameMatches"
                  :key="m.id"
                  style="display:flex;align-items:center;gap:8px;width:100%"
                >
                  <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                    {{ m.title }}
                  </span>
                  <el-tag size="small" effect="plain" type="info">v{{ m.version }}</el-tag>
                  <el-button size="small" type="primary" link @click="linkAsVersion(m)">作为新版本</el-button>
                </div>
              </div>
              <div style="font-size:12px;color:#e6a23c;margin-top:4px">
                若这是该文档的新版本，请点击「作为新版本」；否则将作为独立文档上传。
              </div>
            </el-alert>
          </el-form-item>

          <!-- 授权角色 -->
          <el-form-item label="授权角色">
            <div style="width:100%">
              <el-select
                v-model="uploadForm.addRole"
                placeholder="选择角色授权（自动授权给该角色下的所有用户）"
                clearable
                style="width:100%;margin-bottom:8px"
                @change="handleAddRole"
              >
                <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
              </el-select>
              <div v-if="uploadForm.role_ids.length > 0" style="display:flex;flex-wrap:wrap;gap:6px">
                <el-tag
                  v-for="rid in uploadForm.role_ids"
                  :key="rid"
                  closable
                  type="success"
                  effect="plain"
                  @close="handleRemoveRole(rid)"
                >
                  {{ roleLabel(rid) }}
                </el-tag>
                <span style="font-size:12px;color:#86909c;line-height:28px">
                  （上传后这些角色自动获得查看+下载权限）
                </span>
              </div>
              <div v-if="autoGrantRoleNames(uploadForm.category_id).length" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">
                <el-tag
                  v-for="name in autoGrantRoleNames(uploadForm.category_id)"
                  :key="name"
                  type="warning"
                  effect="plain"
                >{{ name }}</el-tag>
                <span style="font-size:12px;color:#86909c;line-height:28px">
                  （分类默认授权角色，将自动获得查看+下载权限）
                </span>
              </div>
              <div v-if="uploadForm.role_ids.length === 0 && autoGrantRoleNames(uploadForm.category_id).length === 0" style="font-size:12px;color:#c9cdd4;line-height:24px">
                不选择则默认仅上传者和管理员可见
              </div>
            </div>
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="handleSingleSubmit" size="large">
              提交上传
            </el-button>
            <el-button @click="handleSingleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- ========== 批量上传模式 ========== -->
      <div v-else>
        <el-form
          ref="batchFormRef"
          :model="batchForm"
          :rules="batchRules"
          label-width="100px"
          style="max-width: 700px"
        >
          <!-- 文档分类（统一） -->
          <el-form-item label="文档分类" prop="category_id">
            <el-select v-model="batchForm.category_id" placeholder="请选择分类（统一应用到所有文件）" style="width: 100%">
              <el-option
                v-for="item in categoryOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              >
                <span>{{ item.name }}</span>
                <el-tag
                  v-if="isRecommendedCategory(item)"
                  size="small"
                  type="success"
                  effect="plain"
                  style="margin-left: 8px"
                >推荐</el-tag>
              </el-option>
            </el-select>
          </el-form-item>

          <!-- 部门（二级分类，统一） -->
          <el-form-item label="所属部门" prop="department_id">
            <el-select v-model="batchForm.department_id" placeholder="请选择部门（选填，统一应用到所有文件）" clearable style="width: 100%">
              <el-option
                v-for="item in departmentOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <!-- 文档级别（三级分类，统一） -->
          <el-form-item label="文档级别" prop="doc_level">
            <el-select v-model="batchForm.doc_level" placeholder="请选择文档级别（统一应用到所有文件）" style="width: 100%">
              <el-option
                v-for="lv in docLevels"
                :key="lv"
                :label="lv"
                :value="lv"
              />
            </el-select>
          </el-form-item>

          <!-- 保密等级（统一） -->
          <el-form-item label="保密等级" prop="confidential_level">
            <el-radio-group v-model="batchForm.confidential_level">
              <el-radio value="public">公开</el-radio>
              <el-radio value="internal">内部</el-radio>
              <el-radio value="confidential">机密</el-radio>
              <el-radio value="top_secret">绝密</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 文档描述（统一，选填） -->
          <el-form-item label="文档描述">
            <el-input v-model="batchForm.summary" type="textarea" :rows="2" placeholder="请输入统一文档描述（选填）" />
          </el-form-item>

          <!-- 授权角色（统一） -->
          <el-form-item label="授权角色">
            <div style="width:100%">
              <el-select
                v-model="batchForm.addRole"
                placeholder="选择角色授权（统一应用到所有文件）"
                clearable
                style="width:100%;margin-bottom:8px"
                @change="handleBatchAddRole"
              >
                <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
              </el-select>
              <div v-if="batchForm.role_ids.length > 0" style="display:flex;flex-wrap:wrap;gap:6px">
                <el-tag
                  v-for="rid in batchForm.role_ids"
                  :key="rid"
                  closable
                  type="success"
                  effect="plain"
                  @close="handleBatchRemoveRole(rid)"
                >
                  {{ roleLabel(rid) }}
                </el-tag>
                <span style="font-size:12px;color:#86909c;line-height:28px">
                  （所有文件上传后这些角色自动获得查看+下载权限）
                </span>
              </div>
              <div v-if="autoGrantRoleNames(batchForm.category_id).length" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">
                <el-tag
                  v-for="name in autoGrantRoleNames(batchForm.category_id)"
                  :key="name"
                  type="warning"
                  effect="plain"
                >{{ name }}</el-tag>
                <span style="font-size:12px;color:#86909c;line-height:28px">
                  （分类默认授权角色，将自动获得查看+下载权限）
                </span>
              </div>
              <div v-if="batchForm.role_ids.length === 0 && autoGrantRoleNames(batchForm.category_id).length === 0" style="font-size:12px;color:#c9cdd4;line-height:24px">
                不选择则默认仅上传者和管理员可见
              </div>
            </div>
          </el-form-item>

          <!-- 多文件上传 -->
          <el-form-item label="选择文件" prop="fileList">
            <el-upload
              ref="batchUploadRef"
              v-model:file-list="batchFileList"
              :auto-upload="false"
              multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.png,.zip,.rar"
              drag
            >
              <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或 <em>点击选择多个文件</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 PDF、Word、Excel、PPT、TXT、图片、压缩包等格式，可选择多个文件，标题自动取文件名
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <!-- 文件列表预览 -->
          <el-form-item v-if="batchFileList.length > 0" label="待上传文件">
            <div style="width:100%">
              <div style="margin-bottom:8px;font-size:13px;color:#86909c">
                共 {{ batchFileList.length }} 个文件，标题将自动取文件名（不含扩展名）
              </div>
              <el-table :data="batchFileList" size="small" border style="width:100%" max-height="240">
                <el-table-column type="index" label="#" width="50" />
                <el-table-column prop="name" label="文件名" show-overflow-tooltip />
                <el-table-column label="自动标题" width="180">
                  <template #default="{ row }">
                    <el-tag size="small" type="info" effect="plain">
                      {{ getAutoTitle(row.name) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="大小" width="90">
                  <template #default="{ row }">
                    {{ formatSize(row.size) }}
                  </template>
                </el-table-column>
                <el-table-column label="版本关联" min-width="180">
                  <template #default="{ row }">
                    <template v-if="row.parentDoc">
                      <el-tag size="small" type="primary" effect="plain" closable @close="clearBatchVersion(row)">
                        {{ row.parentDoc.title }}
                      </el-tag>
                    </template>
                    <el-button v-else size="small" link type="primary" @click="openBatchVersionPicker(row)">
                      作为新版本
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              :loading="batchSubmitting"
              :disabled="batchFileList.length === 0"
              @click="handleBatchSubmit"
              size="large"
            >
              <template v-if="batchSubmitting">
                上传中...
              </template>
              <template v-else>
                批量上传 ({{ batchFileList.length }} 个文件)
              </template>
            </el-button>
            <el-button @click="handleBatchReset">清空列表</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 批量版本关联选择器 -->
    <el-dialog
      v-model="batchVersionPickerVisible"
      title="选择父文档（作为其新版本上传）"
      width="520px"
      :close-on-click-modal="false"
    >
      <div v-if="batchVersionTarget" style="margin-bottom:10px;font-size:13px;color:#86909c">
        当前文件：<strong>{{ batchVersionTarget.name }}</strong>
      </div>
      <el-select
        v-model="batchVersionParentId"
        filterable
        remote
        :remote-method="queryBatchDocOptions"
        :loading="docSearchLoading"
        placeholder="搜索并选择要关联的父文档"
        style="width:100%"
        clearable
      >
        <el-option
          v-for="doc in docSearchOptions"
          :key="doc.id"
          :label="doc.title"
          :value="doc.id"
        >
          <span>{{ doc.title }}</span>
          <el-tag v-if="doc.version > 1" size="small" effect="plain" style="margin-left:6px">v{{ doc.version }}</el-tag>
        </el-option>
      </el-select>
      <div v-if="batchVersionParentId" style="font-size:12px;color:#86909c;line-height:22px;margin-top:4px">
        新文件将作为选定文档的最新版本，继承其分类/部门/文档级别与授权角色。
      </div>
      <template #footer>
        <el-button @click="batchVersionPickerVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!batchVersionParentId" @click="confirmBatchVersion">确认关联</el-button>
      </template>
    </el-dialog>

    <!-- 批量上传结果对话框 -->
    <el-dialog
      v-model="batchResultVisible"
      title="批量上传结果"
      width="600px"
      :close-on-click-modal="false"
    >
      <div v-if="batchResult" style="margin-bottom:16px">
        <el-alert
          :title="`共 ${batchResult.total} 个文件，成功 ${batchResult.success} 个，失败 ${batchResult.failed} 个`"
          :type="batchResult.failed > 0 ? 'warning' : 'success'"
          :closable="false"
          show-icon
        />
      </div>
      <el-table v-if="batchResult && batchResult.results" :data="batchResult.results" size="small" border max-height="300">
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.success" type="success" size="small">成功</el-tag>
            <el-tag v-else type="danger" size="small">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="250" show-overflow-tooltip v-if="batchResult.failed > 0">
          <template #default="{ row }">
            <span v-if="isDuplicateError(row.error)" style="color:#e6a23c">
              <el-icon style="vertical-align:-2px;margin-right:4px"><WarningFilled /></el-icon>
              文件重复：{{ extractDuplicateTitle(row.error) }}
            </span>
            <span v-else>{{ row.error }}</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="handleBatchResultClose">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重复文件警告对话框 -->
    <el-dialog
      v-model="duplicateDialogVisible"
      title="文件重复提示"
      width="480px"
      :close-on-click-modal="false"
    >
      <div style="text-align:center;padding:16px 0">
        <el-icon :size="48" color="#e6a23c" style="margin-bottom:12px"><WarningFilled /></el-icon>
        <div style="font-size:16px;font-weight:500;margin-bottom:8px">检测到重复文件</div>
        <div style="color:#86909c;font-size:14px;line-height:1.6">
          您正在上传的文件内容与系统中已存在的文档重复：
        </div>
        <div style="margin:12px 0;padding:10px 16px;background:#f7f8fa;border-radius:6px;font-size:14px;text-align:left">
          <div style="margin-bottom:4px">
            <span style="color:#86909c">已存在文档：</span>
            <strong>{{ duplicateInfo.title }}</strong>
          </div>
          <div v-if="duplicateInfo.doc_no">
            <span style="color:#86909c">文档编号：</span>
            <span>{{ duplicateInfo.doc_no }}</span>
          </div>
        </div>
        <div style="color:#86909c;font-size:13px">
          请确认是否需要重复上传，或查看已存在的文档。
        </div>
      </div>
      <template #footer>
        <el-button @click="duplicateDialogVisible = false">取消上传</el-button>
        <el-button type="primary" @click="handleViewDuplicateDoc">查看已存在文档</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'
import { uploadDocument, batchUploadDocuments, getDocLevels, checkSameName, getDocumentList } from '../api/document.js'
import { getCategoryListSimple } from '../api/category.js'
import { getDepartmentSimple } from '../api/department.js'
import { getRoleListSimple } from '../api/role.js'

const router = useRouter()
const authStore = useAuthStore()

// ========== 公共数据 ==========
const uploadMode = ref('single')
const categoryOptions = ref([])
const departmentOptions = ref([])
const docLevels = ref(['无级别'])
const roleOptions = ref([])
const roleMap = ref({})
const submitting = ref(false)

// ========== 版本关联 / 同名提醒 ==========
const versionEnabled = ref(false)
const versionParentId = ref(null)
const versionParentLabel = ref('')
const docSearchOptions = ref([])
const docSearchLoading = ref(false)
const sameNameMatches = ref([])

async function checkSameNameForFile(name) {
  sameNameMatches.value = []
  if (!name) return
  try {
    const res = await checkSameName(name)
    sameNameMatches.value = (res && res.items) || []
  } catch {
    sameNameMatches.value = []
  }
}

function linkAsVersion(m) {
  versionEnabled.value = true
  versionParentId.value = m.id
  versionParentLabel.value = m.title
  sameNameMatches.value = []
  ElMessage.success(`已关联：将作为「${m.title}」的新版本上传`)
}

function handleParentDocChange(val) {
  const d = docSearchOptions.value.find(x => x.id === val)
  versionParentLabel.value = d ? d.title : ''
  if (!val) versionParentLabel.value = ''
}

async function queryDocOptions(keyword) {
  if (!keyword) {
    docSearchOptions.value = []
    return
  }
  docSearchLoading.value = true
  try {
    const res = await getDocumentList({ keyword, page_size: 20, page: 1 })
    const items = (res && (res.items || (res.data && res.data.items))) || []
    const opts = items.map(i => ({ id: i.id, title: i.title, version: i.version || 1 }))
    const ids = new Set(opts.map(x => x.id))
    for (const m of sameNameMatches.value) {
      if (!ids.has(m.id)) opts.push({ id: m.id, title: m.title, version: m.version || 1 })
    }
    docSearchOptions.value = opts
  } catch {
    docSearchOptions.value = []
  } finally {
    docSearchLoading.value = false
  }
}

function clearVersionAssociation() {
  versionEnabled.value = false
  versionParentId.value = null
  versionParentLabel.value = ''
  sameNameMatches.value = []
}

// ========== 重复文件检测 ==========
const duplicateDialogVisible = ref(false)
const duplicateInfo = ref({ title: '', doc_no: '', id: null })

function isDuplicateError(errorMsg) {
  if (!errorMsg) return false
  return errorMsg.includes('文件内容重复') || errorMsg.includes('重复')
}

function extractDuplicateTitle(errorMsg) {
  if (!errorMsg) return ''
  const match = errorMsg.match(/文档标题：「([^」]+)」/)
  return match ? match[1] : errorMsg
}

function handleViewDuplicateDoc() {
  if (duplicateInfo.value.id) {
    duplicateDialogVisible.value = false
    router.push(`/documents/${duplicateInfo.value.id}`)
  }
}

// 用户业务范围
const businessScopes = computed(() => authStore.userInfo?.business_scopes || [])
const isBusinessUser = computed(() => businessScopes.value.length > 0)

function isRecommendedCategory(item) {
  if (!isBusinessUser.value) return false
  return item.business_type && businessScopes.value.includes(item.business_type)
}

function roleLabel(rid) {
  return roleMap.value[rid] || `#${rid}`
}

// 分类默认授权角色名称（选中分类后提示将自动授权的角色）
function autoGrantRoleNames(categoryId) {
  const cat = categoryOptions.value.find(c => c.id === categoryId)
  if (!cat || !Array.isArray(cat.default_role_ids) || cat.default_role_ids.length === 0) return []
  return cat.default_role_ids.map(rid => roleMap.value[rid] || `#${rid}`)
}

// ========== 单文件上传 ==========
const uploadFormRef = ref(null)
const uploadRef = ref(null)
const uploadForm = reactive({
  title: '',
  doc_no: '',
  category_id: '',
  department_id: '',
  doc_level: '无级别',
  confidential_level: 'internal',
  summary: '',
  file: null,
  role_ids: [],
  addRole: null,
})

const uploadRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' },
    { max: 200, message: '标题长度不能超过 200 字符', trigger: 'blur' }
  ],
  category_id: [{ required: true, message: '请选择文档分类', trigger: 'change' }],
  confidential_level: [{ required: true, message: '请选择保密等级', trigger: 'change' }]
}

function handleFileChange(file) {
  uploadForm.file = file.raw
  if (!uploadForm.title) {
    const name = file.name.substring(0, file.name.lastIndexOf('.')) || file.name
    uploadForm.title = name
  }
  checkSameNameForFile(file.name)
}

function handleFileRemove() {
  uploadForm.file = null
}

function handleAddRole(roleId) {
  if (!roleId) return
  if (uploadForm.role_ids.includes(roleId)) {
    ElMessage.warning('该角色已添加')
    uploadForm.addRole = null
    return
  }
  uploadForm.role_ids.push(roleId)
  uploadForm.addRole = null
}

function handleRemoveRole(rid) {
  uploadForm.role_ids = uploadForm.role_ids.filter(id => id !== rid)
}

async function handleSingleSubmit() {
  if (!uploadFormRef.value) return
  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (!uploadForm.file) {
      ElMessage.warning('请选择要上传的文件')
      return
    }
    submitting.value = true
    try {
      const formData = new FormData()
      formData.append('file', uploadForm.file)
      formData.append('title', uploadForm.title)
      if (uploadForm.doc_no) formData.append('doc_no', uploadForm.doc_no)
      formData.append('category_id', uploadForm.category_id)
      if (uploadForm.department_id) formData.append('department_id', uploadForm.department_id)
      formData.append('doc_level', uploadForm.doc_level)
      formData.append('confidential_level', uploadForm.confidential_level)
      if (uploadForm.summary) formData.append('summary', uploadForm.summary)
      if (uploadForm.role_ids.length > 0) {
        formData.append('role_ids', uploadForm.role_ids.join(','))
      }
      if (versionEnabled.value && versionParentId.value) {
        formData.append('parent_doc_id', versionParentId.value)
      }
      await uploadDocument(formData)
      ElMessage.success('文档上传成功')
      router.push('/documents')
    } catch (err) {
      // 检查是否为重复文件错误（409 Conflict）
      const detail = err?.errorMessage
      if (detail && detail.duplicate_doc_id) {
        duplicateInfo.value = {
          id: detail.duplicate_doc_id,
          title: detail.duplicate_title || '未知',
          doc_no: '',
        }
        duplicateDialogVisible.value = true
      } else {
        // 其他错误由 request.js 统一处理，这里不做额外操作
      }
    } finally {
      submitting.value = false
    }
  })
}

function handleSingleReset() {
  uploadForm.title = ''
  uploadForm.doc_no = ''
  uploadForm.category_id = ''
  uploadForm.department_id = ''
  uploadForm.doc_level = '无级别'
  uploadForm.confidential_level = 'internal'
  uploadForm.summary = ''
  uploadForm.file = null
  uploadForm.role_ids = []
  clearVersionAssociation()
  if (uploadRef.value) uploadRef.value.clearFiles()
  if (isBusinessUser.value) {
    const recommended = categoryOptions.value.find(item => isRecommendedCategory(item))
    if (recommended) uploadForm.category_id = recommended.id
  }
}

// ========== 批量上传 ==========
const batchFormRef = ref(null)
const batchUploadRef = ref(null)
const batchSubmitting = ref(false)
const batchFileList = ref([])
const batchResultVisible = ref(false)
const batchResult = ref(null)

const batchForm = reactive({
  category_id: '',
  department_id: '',
  doc_level: '无级别',
  confidential_level: 'internal',
  summary: '',
  role_ids: [],
  addRole: null,
})

const batchRules = {
  category_id: [{ required: true, message: '请选择文档分类', trigger: 'change' }],
  confidential_level: [{ required: true, message: '请选择保密等级', trigger: 'change' }],
}

function getAutoTitle(fileName) {
  if (!fileName) return ''
  const dotIndex = fileName.lastIndexOf('.')
  return dotIndex > 0 ? fileName.substring(0, dotIndex) : fileName
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function handleBatchAddRole(roleId) {
  if (!roleId) return
  if (batchForm.role_ids.includes(roleId)) {
    ElMessage.warning('该角色已添加')
    batchForm.addRole = null
    return
  }
  batchForm.role_ids.push(roleId)
  batchForm.addRole = null
}

function handleBatchRemoveRole(rid) {
  batchForm.role_ids = batchForm.role_ids.filter(id => id !== rid)
}

// ========== 批量版本关联（逐文件） ==========
const batchVersionPickerVisible = ref(false)
const batchVersionTarget = ref(null)
const batchVersionParentId = ref(null)

function openBatchVersionPicker(row) {
  batchVersionTarget.value = row
  batchVersionParentId.value = row.parentDoc ? row.parentDoc.id : null
  docSearchOptions.value = []
  batchVersionPickerVisible.value = true
}

async function queryBatchDocOptions(keyword) {
  await queryDocOptions(keyword)
}

function confirmBatchVersion() {
  if (!batchVersionTarget.value || !batchVersionParentId.value) return
  const d = docSearchOptions.value.find(x => x.id === batchVersionParentId.value)
  batchVersionTarget.value.parentDoc = {
    id: batchVersionParentId.value,
    title: d ? d.title : `#${batchVersionParentId.value}`,
  }
  batchVersionPickerVisible.value = false
  batchVersionTarget.value = null
  batchVersionParentId.value = null
}

function clearBatchVersion(row) {
  row.parentDoc = null
}

async function handleBatchSubmit() {
  if (!batchFormRef.value) return
  await batchFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (batchFileList.value.length === 0) {
      ElMessage.warning('请选择要上传的文件')
      return
    }

    batchSubmitting.value = true

    try {
      const formData = new FormData()
      for (const f of batchFileList.value) {
        formData.append('files', f.raw)
      }
      formData.append('category_id', batchForm.category_id)
      if (batchForm.department_id) formData.append('department_id', batchForm.department_id)
      formData.append('doc_level', batchForm.doc_level)
      formData.append('confidential_level', batchForm.confidential_level)
      if (batchForm.summary) formData.append('summary', batchForm.summary)
      if (batchForm.role_ids.length > 0) {
        formData.append('role_ids', batchForm.role_ids.join(','))
      }
      // 逐文件版本关联：按文件列表顺序逗号分隔父文档ID，无关联的文件用空占位
      if (batchFileList.value.some(f => f.parentDoc && f.parentDoc.id)) {
        formData.append('parent_doc_ids', batchFileList.value.map(f => (f.parentDoc && f.parentDoc.id) ? f.parentDoc.id : '').join(','))
      }

      const result = await batchUploadDocuments(formData)
      batchResult.value = result
      batchResultVisible.value = true

      if (result.failed === 0) {
        ElMessage.success(`批量上传成功，共上传 ${result.success} 个文件`)
      } else {
        ElMessage.warning(`上传完成：${result.success} 个成功，${result.failed} 个失败`)
      }
    } catch {
    } finally {
      batchSubmitting.value = false
    }
  })
}

function handleBatchReset() {
  batchFileList.value = []
  batchForm.department_id = ''
  batchForm.doc_level = '无级别'
  batchForm.summary = ''
  batchForm.role_ids = []
  batchResult.value = null
  if (batchUploadRef.value) batchUploadRef.value.clearFiles()
}

function handleBatchResultClose() {
  batchResultVisible.value = false
  if (batchResult.value && batchResult.value.failed === 0) {
    router.push('/documents')
  } else {
    handleBatchReset()
  }
}

// ========== 初始化 ==========
onMounted(async () => {
  try {
    const res = await getCategoryListSimple()
    categoryOptions.value = res.items || res.data || res || []
    if (isBusinessUser.value) {
      const recommended = categoryOptions.value.find(item => isRecommendedCategory(item))
      if (recommended) {
        uploadForm.category_id = recommended.id
        batchForm.category_id = recommended.id
      }
    }
  } catch { /* ignore */ }
  try {
    const deptRes = await getDepartmentSimple()
    const list = deptRes.items || deptRes.data || deptRes || []
    departmentOptions.value = Array.isArray(list) ? list : []
  } catch { /* ignore */ }
  try {
    const levelRes = await getDocLevels()
    if (levelRes && Array.isArray(levelRes.levels) && levelRes.levels.length > 0) {
      docLevels.value = levelRes.levels
    }
  } catch { /* ignore */ }
  try {
    const roles = await getRoleListSimple()
    roleOptions.value = roles
    for (const r of roles) {
      roleMap.value[r.id] = r.name
    }
  } catch { /* ignore */ }
})
</script>

<style scoped>
.category-filter-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #86909c;
}
</style>
