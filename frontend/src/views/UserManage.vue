<template>
  <div class="user-manage">
    <!-- 搜索栏 -->
    <el-card shadow="never">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索用户名/姓名"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="searchForm.department_id" placeholder="全部部门" clearable style="width: 160px">
            <el-option
              v-for="item in departmentOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role_id" placeholder="全部角色" clearable style="width: 140px">
            <el-option
              v-for="item in roleOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="全部状态" clearable style="width: 100px">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="userList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="姓名" width="100" />
        <el-table-column label="部门" width="120">
          <template #default="{ row }">
            {{ row.department?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role?.name)" size="small">
              {{ row.role?.name || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="table-op-btns">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="warning" link size="small" @click="handleResetPwd(row)">重置密码</el-button>
            <el-button
              :type="row.is_active ? 'danger' : 'success'"
              link
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">彻底删除</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="550px"
      destroy-on-close
      draggable
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="formData.display_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="formData.department_id" placeholder="请选择部门" style="width: 100%">
            <el-option
              v-for="item in departmentOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="formData.role_id" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="item in roleOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="附加角色">
          <el-select
            v-model="formData.role_ids"
            multiple
            placeholder="可多选附加角色"
            style="width: 100%"
          >
            <el-option
              v-for="item in roleOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!editingId" label="密码" prop="password">
          <el-input v-model="formData.password" type="password" placeholder="请设置密码" show-password />
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
 * 用户管理页面
 * 系统管理员可对用户进行增删改查、重置密码、启用/禁用等操作
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import {
  getUserList, createUser, updateUser, deleteUser,
  resetUserPassword, toggleUserStatus
} from '../api/user.js'
import { getDepartmentList } from '../api/department.js'
import { getRoleList } from '../api/role.js'

// 状态
const loading = ref(false)
const submitting = ref(false)
const userList = ref([])
const departmentOptions = ref([])
const roleOptions = ref([])

// 分页
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

// 搜索
const searchForm = reactive({
  keyword: '',
  department_id: '',
  role_id: '',
  is_active: ''
})

// 对话框
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const dialogTitle = computed(() => editingId.value ? '编辑用户' : '新增用户')

// 表单数据
const formData = reactive({
  username: '',
  display_name: '',
  department_id: '',
  role_id: '',
  role_ids: [],
  password: ''
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 个字符', trigger: 'blur' }
  ],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ]
}

/**
 * 角色标签类型
 */
function roleTagType(roleName) {
  const map = { '系统管理员': 'danger', '文档管理员': 'warning', '部门管理员': '', '普通用户': 'info' }
  return map[roleName] || 'info'
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      department_id: searchForm.department_id || undefined,
      role_id: searchForm.role_id || undefined,
      is_active: searchForm.is_active !== '' ? searchForm.is_active : undefined
    }
    const res = await getUserList(params)
    userList.value = res.items || res.data || []
    pagination.total = res.total || 0
  } catch (error) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function fetchDepartments() {
  try {
    const res = await getDepartmentList({ page_size: 100 })
    departmentOptions.value = res.items || res.data || res || []
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

async function fetchRoles() {
  try {
    const res = await getRoleList()
    roleOptions.value = res || []
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

function handleSearch() {
  pagination.page = 1
  fetchUsers()
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.department_id = ''
  searchForm.role_id = ''
  searchForm.is_active = ''
  pagination.page = 1
  fetchUsers()
}

function handleAdd() {
  editingId.value = null
  formData.username = ''
  formData.display_name = ''
  formData.department_id = ''
  formData.role_id = ''
  formData.role_ids = []
  formData.password = ''
  dialogVisible.value = true
}

function handleEdit(row) {
  editingId.value = row.id
  formData.username = row.username
  formData.display_name = row.display_name || ''
  formData.department_id = row.department?.id || ''
  formData.role_id = row.role?.id || ''
  formData.role_ids = (row.roles || []).map((r) => r.id).filter((id) => id !== formData.role_id)
  formData.password = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data = {
        username: formData.username,
        display_name: formData.display_name,
        department_id: formData.department_id || undefined,
        role_id: formData.role_id || undefined,
        role_ids: formData.role_ids,
      }
      if (editingId.value) {
        await updateUser(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        data.password = formData.password
        await createUser(data)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchUsers()
    } catch (error) {
      // 错误已在拦截器中处理
    } finally {
      submitting.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${row.display_name || row.username}」吗？`, '删除确认', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    // 用户取消或错误
  }
}

async function handleResetPwd(row) {
  try {
    const { value } = await ElMessageBox.prompt(
      `请为用户「${row.display_name || row.username}」设置新密码（至少6位）`,
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^.{6,}$/,
        inputErrorMessage: '密码长度不能少于 6 位'
      }
    )
    await resetUserPassword(row.id, { new_password: value })
    ElMessage.success('密码重置成功')
  } catch (error) {
    // 用户取消或错误
  }
}

async function handleToggleStatus(row) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.display_name || row.username}」吗？`,
      `${action}确认`,
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await toggleUserStatus(row.id, { is_active: !row.is_active })
    ElMessage.success(`${action}成功`)
    fetchUsers()
  } catch (error) {
    // 用户取消或错误
  }
}

function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchUsers()
}

function handlePageChange(page) {
  pagination.page = page
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
  fetchDepartments()
  fetchRoles()
})
</script>

<style scoped>
.user-manage {
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
