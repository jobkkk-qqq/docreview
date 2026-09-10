<template>
  <div class="category-manage">
    <!-- 三级分类结构概览 -->
    <el-card shadow="never" class="structure-card">
      <div class="card-header">
        <span class="structure-title">三级分类结构</span>
        <div class="structure-hint">一级：文档分类　·　二级：部门分类　·　三级：文档级别</div>
      </div>
      <div class="structure-levels" v-loading="structureLoading">
        <!-- 一级分类 -->
        <div class="level-row">
          <div class="level-badge level-1">一级</div>
          <div class="level-body">
            <div class="level-name">文档分类</div>
            <div class="level-desc">在下方表格中维护，用于文档上传与权限控制</div>
          </div>
          <el-button type="primary" link :disabled="categoryList.length === 0" @click="scrollToTable">共 {{ pagination.total || categoryList.length }} 项</el-button>
        </div>

        <!-- 二级部门 -->
        <div class="level-row">
          <div class="level-badge level-2">二级</div>
          <div class="level-body">
            <div class="level-name">部门分类</div>
            <div class="level-desc">引用「部门管理」中的部门，文档可归属到具体部门</div>
            <div class="level-tags" v-if="departmentOptions.length">
              <el-tag v-for="d in departmentOptions" :key="d.id" size="small" effect="plain">{{ d.name }}</el-tag>
            </div>
            <el-tag v-else size="small" type="info" effect="plain">暂无部门</el-tag>
          </div>
          <el-button type="primary" link @click="$router.push('/departments')">
            共 {{ departmentOptions.length }} 项 管理
          </el-button>
        </div>

        <!-- 三级文档级别 -->
        <div class="level-row">
          <div class="level-badge level-3">三级</div>
          <div class="level-body">
            <div class="level-name">文档级别</div>
            <div class="level-desc">系统预设的文档保密级别，用于文档分级标识</div>
            <div class="level-tags">
              <el-tag v-for="lv in docLevels" :key="lv" size="small" type="primary" effect="plain">{{ lv }}</el-tag>
            </div>
          </div>
          <span class="level-fixed">固定预设</span>
        </div>
      </div>
    </el-card>

    <!-- 操作栏 -->
    <el-card shadow="never" class="search-card" id="category-table-card">
      <div class="card-header">
        <span>分类管理</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增分类</el-button>
      </div>
    </el-card>

    <!-- 分类列表 -->
    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="categoryList"
        border
        stripe
        row-key="id"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="分类名称" min-width="140" />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="业务类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.business_type" type="primary" size="small">{{ row.business_type }}</el-tag>
            <span v-else style="color:#86909c">-</span>
          </template>
        </el-table-column>
        <el-table-column label="全员可见" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_public" type="success" size="small">是</el-tag>
            <span v-else style="color:#86909c">-</span>
          </template>
        </el-table-column>
        <el-table-column label="默认授权角色" min-width="150">
          <template #default="{ row }">
            <template v-if="row.default_role_ids && row.default_role_ids.length">
              <el-tag
                v-for="rid in row.default_role_ids"
                :key="rid"
                size="small"
                type="warning"
                effect="plain"
                style="margin-right:4px"
              >{{ roleName(rid) }}</el-tag>
            </template>
            <span v-else style="color:#86909c">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="doc_count" label="文档数量" width="100" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openPerm(row)">权限</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入分类描述"
          />
        </el-form-item>
        <el-form-item label="业务类型" prop="business_type">
          <el-select v-model="formData.business_type" placeholder="请选择业务类型" clearable style="width: 100%">
            <el-option label="品质（quality）" value="quality" />
            <el-option label="行政（admin）" value="admin" />
            <el-option label="人事（hr）" value="hr" />
            <el-option label="财务（finance）" value="finance" />
            <el-option label="法务（legal）" value="legal" />
            <el-option label="采购（procurement）" value="procurement" />
            <el-option label="生产（production）" value="production" />
          </el-select>
          <div style="margin-top:4px;font-size:12px;color:#86909c">
            与角色业务范围一致时，该角色用户才能上传到此分类
          </div>
        </el-form-item>
        <el-form-item label="默认授权角色" prop="default_role_ids">
          <el-select
            v-model="formData.default_role_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="不选则仅上传时手动授权的角色可见"
            style="width: 100%"
          >
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
          <div style="margin-top:4px;font-size:12px;color:#86909c">
            上传到该分类的新文档将自动授予这些角色 查看+下载 权限；单个文档可在权限矩阵中单独调整
          </div>
        </el-form-item>
        <el-form-item label="全员可见" prop="is_public">
          <el-switch
            v-model="formData.is_public"
            active-text="是"
            inactive-text="否"
          />
          <span style="margin-left:12px;font-size:12px;color:#86909c">
            开启后，所有登录用户默认可查看该分类下的文档
          </span>
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="formData.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分类权限管理对话框 -->
    <el-dialog
      v-model="permDialogVisible"
      :title="permDialogTitle"
      width="640px"
      destroy-on-close
      @closed="resetPermForm"
    >
      <div class="perm-desc">
        授权后，所授角色/用户可查看或编辑该分类下的全部文档（查看包含下载），适用于现存及新上传文档。
      </div>

      <!-- 新增授权 -->
      <el-form :inline="true" class="perm-grant-form">
        <el-form-item label="角色">
          <el-select v-model="grantRoleId" placeholder="选择角色" clearable filterable style="width: 160px">
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户">
          <el-select
            v-model="grantUserId"
            placeholder="搜索用户"
            clearable
            filterable
            remote
            :remote-method="searchUsers"
            :loading="usersLoading"
            style="width: 160px"
          >
            <el-option v-for="u in userOptions" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox v-model="grantCanView">查看</el-checkbox>
          <el-checkbox v-model="grantCanEdit">编辑</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="permSubmitting" @click="addCategoryPerm">添加授权</el-button>
        </el-form-item>
      </el-form>

      <!-- 授权列表 -->
      <el-table :data="catPerms" v-loading="permLoading" size="small" border>
        <el-table-column label="授权对象" min-width="160">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role_id ? 'primary' : 'info'" effect="plain">
              {{ row.role_id ? '角色' : '用户' }}
            </el-tag>
            <span style="margin-left:6px">{{ row.role_name || row.user_name || `ID:${row.role_id || row.user_id}` }}</span>
          </template>
        </el-table-column>
        <el-table-column label="查看" width="70" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.can_view" @change="(v) => togglePerm(row, 'can_view', v)" />
          </template>
        </el-table-column>
        <el-table-column label="编辑" width="70" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.can_edit" @change="(v) => togglePerm(row, 'can_edit', v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="removeCategoryPerm(row)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 分类管理页面
 * 系统管理员和文档管理员可管理文档分类
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getCategoryList, createCategory, updateCategory, deleteCategory } from '../api/category.js'
import { getDepartmentSimple } from '../api/department.js'
import {
  getDocLevels,
  getCategoryPermissions,
  grantCategoryPermission,
  revokeCategoryPermission
} from '../api/document.js'
import { getRoleListSimple } from '../api/role.js'
import { getUserList } from '../api/user.js'

// 加载状态
const loading = ref(false)
const submitting = ref(false)
const structureLoading = ref(false)

// 三级分类结构数据
const departmentOptions = ref([])
const docLevels = ref(['无级别'])

// 角色选项（默认授权角色多选）
const roleOptions = ref([])
const roleMap = ref({})
const roleName = (rid) => roleMap.value[rid] || `角色${rid}`

// 分类列表
const categoryList = ref([])

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const dialogTitle = computed(() => editingId.value ? '编辑分类' : '新增分类')

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  business_type: '',
  is_public: false,
  default_role_ids: [],
  sort_order: 0
})

// 校验规则
const formRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 50, message: '名称长度不能超过 50 字符', trigger: 'blur' }
  ]
}

/**
 * 加载分类列表
 */
async function fetchList() {
  loading.value = true
  try {
    const res = await getCategoryList({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    categoryList.value = res.items || res.data || res || []
    pagination.total = res.total || 0
  } catch (error) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

/**
 * 新增
 */
function handleAdd() {
  editingId.value = null
  formData.name = ''
  formData.description = ''
  formData.business_type = ''
  formData.is_public = false
  formData.default_role_ids = []
  formData.sort_order = 0
  dialogVisible.value = true
}

/**
 * 编辑
 */
function handleEdit(row) {
  editingId.value = row.id
  formData.name = row.name
  formData.description = row.description || ''
  formData.business_type = row.business_type || ''
  formData.is_public = row.is_public || false
  formData.default_role_ids = Array.isArray(row.default_role_ids) ? [...row.default_role_ids] : []
  formData.sort_order = row.sort_order || 0
  dialogVisible.value = true
}

/**
 * 提交
 */
async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data = {
        name: formData.name,
        description: formData.description,
        business_type: (formData.business_type || '').trim() || null,
        is_public: formData.is_public,
        sort_order: formData.sort_order,
        default_role_ids: formData.default_role_ids
      }
      if (editingId.value) {
        await updateCategory(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await createCategory(data)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchList()
    } catch (error) {
      // 错误已在拦截器中处理
    } finally {
      submitting.value = false
    }
  })
}

/**
 * 删除
 */
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除分类「${row.name}」吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteCategory(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (error) {
    // 用户取消或错误
  }
}

function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchList()
}

function handlePageChange(page) {
  pagination.page = page
  fetchList()
}

function scrollToTable() {
  document.getElementById('category-table-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/**
 * 加载三级分类结构数据（部门、文档级别）
 */
async function fetchStructure() {
  structureLoading.value = true
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
  structureLoading.value = false
}

/**
 * 加载角色选项（默认授权角色多选）
 */
async function fetchRoles() {
  try {
    const roles = await getRoleListSimple()
    roleOptions.value = roles || []
    for (const r of roleOptions.value) {
      roleMap.value[r.id] = r.name
    }
  } catch { /* ignore */ }
}

// ── 分类权限管理 ────────────────────────────────────────
const permDialogVisible = ref(false)
const permCategory = ref(null)
const permLoading = ref(false)
const permSubmitting = ref(false)
const catPerms = ref([])
const grantRoleId = ref(null)
const grantUserId = ref(null)
const grantCanView = ref(true)
const grantCanEdit = ref(false)
const userOptions = ref([])
const usersLoading = ref(false)

const permDialogTitle = computed(() =>
  permCategory.value ? `分类权限 - ${permCategory.value.name}` : '分类权限'
)

function resetPermForm() {
  grantRoleId.value = null
  grantUserId.value = null
  grantCanView.value = true
  grantCanEdit.value = false
  userOptions.value = []
}

function openPerm(row) {
  permCategory.value = row
  resetPermForm()
  permDialogVisible.value = true
  loadCatPerms()
}

async function loadCatPerms() {
  if (!permCategory.value) return
  permLoading.value = true
  try {
    const res = await getCategoryPermissions(permCategory.value.id)
    catPerms.value = Array.isArray(res) ? res : []
  } catch { /* 错误已在拦截器处理 */ } finally {
    permLoading.value = false
  }
}

async function searchUsers(keyword) {
  if (!keyword) return
  usersLoading.value = true
  try {
    const res = await getUserList({ keyword, page_size: 20 })
    userOptions.value = res.items || res.data || []
  } catch { /* ignore */ } finally {
    usersLoading.value = false
  }
}

async function addCategoryPerm() {
  if (!grantRoleId.value && !grantUserId.value) {
    ElMessage.warning('请选择要授权的角色或用户')
    return
  }
  if (!grantCanView.value && !grantCanEdit.value) {
    ElMessage.warning('请至少勾选查看或编辑权限')
    return
  }
  permSubmitting.value = true
  try {
    await grantCategoryPermission({
      category_id: permCategory.value.id,
      role_id: grantRoleId.value || null,
      user_id: grantUserId.value || null,
      can_view: grantCanView.value,
      can_edit: grantCanEdit.value
    })
    ElMessage.success('授权成功')
    resetPermForm()
    loadCatPerms()
  } catch { /* 错误已在拦截器处理 */ } finally {
    permSubmitting.value = false
  }
}

async function togglePerm(perm, field, value) {
  if (!value && !perm.can_view && !perm.can_edit) {
    ElMessage.warning('至少保留查看或编辑权限，如需取消请点重置')
    return
  }
  try {
    await grantCategoryPermission({
      category_id: perm.category_id,
      role_id: perm.role_id || null,
      user_id: perm.user_id || null,
      can_view: perm.can_view,
      can_edit: perm.can_edit
    })
    ElMessage.success('权限已更新')
  } catch {
    perm[field] = !value
  }
}

async function removeCategoryPerm(perm) {
  try {
    await ElMessageBox.confirm('确定撤销该对象在此分类下的权限吗？', '撤销确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await revokeCategoryPermission(perm.id)
    ElMessage.success('权限已撤销')
    loadCatPerms()
  } catch { /* 用户取消或错误 */ }
}

onMounted(() => {
  fetchList()
  fetchStructure()
  fetchRoles()
})
</script>

<style scoped>
.category-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.perm-desc {
  margin-bottom: 12px;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
}

.perm-grant-form {
  margin-bottom: 12px;
}

.structure-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}

.structure-hint {
  font-size: 12px;
  color: #86909c;
}

.structure-levels {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 60px;
}

.level-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafbfc;
}

.level-badge {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}

.level-badge.level-1 { background: linear-gradient(135deg, #165dff, #2b6df6); }
.level-badge.level-2 { background: linear-gradient(135deg, #13c2c2, #0aa5a5); }
.level-badge.level-3 { background: linear-gradient(135deg, #722ed1, #531dab); }

.level-body {
  flex: 1;
  min-width: 0;
}

.level-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.level-desc {
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
}

.level-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.level-fixed {
  flex-shrink: 0;
  align-self: center;
  font-size: 12px;
  color: #86909c;
  background: #f0f0f0;
  padding: 4px 10px;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
