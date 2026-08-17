<template>
  <div class="department-manage">
    <!-- 操作栏 -->
    <el-card shadow="never">
      <div class="card-header">
        <span>部门管理</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增部门</el-button>
      </div>
    </el-card>

    <!-- 部门列表 -->
    <el-card shadow="never">
      <el-table v-loading="loading" :data="departmentList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="部门名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="user_count" label="员工数量" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="450px"
      destroy-on-close
      draggable
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="80px">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入部门描述"
          />
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
 * 部门管理页面
 * 系统管理员可管理部门信息
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getDepartmentList, createDepartment, updateDepartment, deleteDepartment } from '../api/department.js'

const loading = ref(false)
const submitting = ref(false)
const departmentList = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const dialogTitle = computed(() => editingId.value ? '编辑部门' : '新增部门')

const formData = reactive({
  name: '',
  description: ''
})

const formRules = {
  name: [
    { required: true, message: '请输入部门名称', trigger: 'blur' },
    { max: 50, message: '名称长度不能超过 50 字符', trigger: 'blur' }
  ]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getDepartmentList({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    departmentList.value = res.items || res.data || res || []
    pagination.total = res.total || 0
  } catch (error) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  editingId.value = null
  formData.name = ''
  formData.description = ''
  dialogVisible.value = true
}

function handleEdit(row) {
  editingId.value = row.id
  formData.name = row.name
  formData.description = row.description || ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data = {
        name: formData.name,
        description: formData.description
      }
      if (editingId.value) {
        await updateDepartment(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await createDepartment(data)
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

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除部门「${row.name}」吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteDepartment(row.id)
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
.department-manage {
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
