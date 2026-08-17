<template>
  <div class="category-manage">
    <!-- 操作栏 -->
    <el-card shadow="never" class="search-card">
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

// 加载状态
const loading = ref(false)
const submitting = ref(false)

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

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.category-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
