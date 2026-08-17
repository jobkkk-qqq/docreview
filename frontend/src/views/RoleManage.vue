<template>
  <div class="role-manage">
    <!-- 操作栏 -->
    <el-card shadow="never">
      <div class="card-header">
        <span>角色管理</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增角色</el-button>
      </div>
    </el-card>

    <!-- 角色列表 -->
    <el-card shadow="never">
      <el-table v-loading="loading" :data="roleList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="角色名称" width="140" />
        <el-table-column prop="code" label="角色编码" width="130" />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="业务角色" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_business_role" type="success" size="small">是</el-tag>
            <span v-else style="color:#86909c">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="business_scope" label="业务范围" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.business_scope" type="primary" size="small">{{ row.business_scope }}</el-tag>
            <span v-else style="color:#86909c">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="关联用户数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.is_system"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
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
      width="500px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="80px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input
            v-model="formData.code"
            placeholder="英文唯一标识，如 doc_admin（选填，留空自动生成）"
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入角色描述"
          />
        </el-form-item>
        <el-form-item label="业务角色" prop="is_business_role">
          <el-switch
            v-model="formData.is_business_role"
            active-text="是"
            inactive-text="否"
          />
          <span style="margin-left:12px;font-size:12px;color:#86909c">
            开启后，拥有该角色的用户只能维护对应业务类型的分类
          </span>
        </el-form-item>
        <el-form-item v-if="formData.is_business_role" label="业务范围" prop="business_scope">
          <div style="display:flex;align-items:center;gap:8px;width:100%">
            <el-select v-model="formData.business_scope" placeholder="请选择业务范围" style="flex:1">
              <el-option
                v-for="item in businessScopeOptions"
                :key="item.code"
                :label="item.name + '（' + item.code + '）'"
                :value="item.code"
              />
            </el-select>
            <el-button type="primary" link size="small" @click="openScopeDialog">管理</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 业务范围管理对话框 -->
    <el-dialog
      v-model="scopeDialogVisible"
      title="业务范围管理"
      width="600px"
      destroy-on-close
    >
      <div style="margin-bottom: 16px; display: flex; gap: 8px">
        <el-button type="primary" :icon="Plus" @click="addScopeItem">新增</el-button>
        <el-button type="warning" @click="restoreDefaults">恢复默认</el-button>
      </div>
      <el-table :data="scopeList" border stripe style="width: 100%">
        <el-table-column prop="code" label="编码" width="150">
          <template #default="{ row, $index }">
            <el-input v-model="row.code" placeholder="如 quality" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.name" placeholder="如 品质" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ $index }">
            <el-button type="danger" link size="small" @click="removeScopeItem($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="scopeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="scopeSubmitting" @click="handleSaveScopes">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 角色管理页面
 * 系统管理员可管理角色基本信息与业务身份配置
 * 菜单功能权限统一在「权限矩阵」中配置
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getRoleFullList, createRole, updateRole, deleteRole, getBusinessScopes, saveBusinessScopes } from '../api/system.js'

const loading = ref(false)
const submitting = ref(false)
const roleList = ref([])
const businessScopeOptions = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)

// 业务范围管理
const scopeDialogVisible = ref(false)
const scopeSubmitting = ref(false)
const scopeList = ref([])

const dialogTitle = computed(() => editingId.value ? '编辑角色' : '新增角色')

const formData = reactive({
  name: '',
  code: '',
  description: '',
  is_business_role: false,
  business_scope: ''
})

const formRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' }
  ]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getRoleFullList({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    roleList.value = res.items || res.data || res || []
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
  formData.code = ''
  formData.description = ''
  formData.is_business_role = false
  formData.business_scope = ''
  dialogVisible.value = true
}

function handleEdit(row) {
  editingId.value = row.id
  formData.name = row.name
  formData.code = row.code
  formData.description = row.description || ''
  formData.is_business_role = row.is_business_role || false
  formData.business_scope = row.business_scope || ''
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
        code: formData.code,
        description: formData.description,
        is_business_role: formData.is_business_role,
        business_scope: formData.is_business_role ? (formData.business_scope || '').trim() : null
      }
      if (editingId.value) {
        await updateRole(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await createRole(data)
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
  if (row.is_system) {
    ElMessage.warning('系统内置角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除角色「${row.name}」吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteRole(row.id)
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

// ── 业务范围管理 ────────────────────────────────────────────

async function fetchBusinessScopes() {
  try {
    const res = await getBusinessScopes()
    businessScopeOptions.value = res.items || []
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

function openScopeDialog() {
  // 深拷贝当前列表，避免直接修改
  scopeList.value = JSON.parse(JSON.stringify(businessScopeOptions.value))
  scopeDialogVisible.value = true
}

function addScopeItem() {
  scopeList.value.push({ code: '', name: '' })
}

function removeScopeItem(index) {
  scopeList.value.splice(index, 1)
}

// 默认业务范围列表
const DEFAULT_SCOPES = [
  { code: 'quality', name: '品质' },
  { code: 'admin', name: '行政' },
  { code: 'hr', name: '人事' },
  { code: 'finance', name: '财务' },
  { code: 'legal', name: '法务' },
  { code: 'procurement', name: '采购' },
  { code: 'production', name: '生产' },
]

function restoreDefaults() {
  scopeList.value = JSON.parse(JSON.stringify(DEFAULT_SCOPES))
  ElMessage.success('已恢复默认业务范围，点击保存生效')
}

async function handleSaveScopes() {
  // 校验
  for (const item of scopeList.value) {
    if (!item.code || !item.name) {
      ElMessage.warning('编码和名称不能为空')
      return
    }
    if (!/^[a-zA-Z0-9_]+$/.test(item.code)) {
      ElMessage.warning(`编码 "${item.code}" 只能包含字母、数字和下划线`)
      return
    }
  }
  // 检查 code 重复
  const codes = scopeList.value.map(i => i.code)
  if (new Set(codes).size !== codes.length) {
    ElMessage.warning('存在重复的编码，请检查')
    return
  }

  scopeSubmitting.value = true
  try {
    await saveBusinessScopes({ items: scopeList.value })
    ElMessage.success('保存成功')
    scopeDialogVisible.value = false
    await fetchBusinessScopes()
  } catch (error) {
    // 错误已在拦截器中处理
  } finally {
    scopeSubmitting.value = false
  }
}

onMounted(() => {
  fetchList()
  fetchBusinessScopes()
})
</script>

<style scoped>
.role-manage {
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
