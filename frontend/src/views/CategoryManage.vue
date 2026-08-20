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
        <el-table-column prop="doc_count" label="文档数量" width="100" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
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
import { getDocLevels } from '../api/document.js'

// 加载状态
const loading = ref(false)
const submitting = ref(false)
const structureLoading = ref(false)

// 三级分类结构数据
const departmentOptions = ref([])
const docLevels = ref(['无级别'])

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
        sort_order: formData.sort_order
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

onMounted(() => {
  fetchList()
  fetchStructure()
})
</script>

<style scoped>
.category-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
