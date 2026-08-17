<template>
  <div class="perm-matrix">
    <!-- 操作栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-icon :size="18" color="#165dff"><Setting /></el-icon>
          <span style="font-size:15px;font-weight:600">权限矩阵</span>
          <el-tag size="small" type="info" effect="plain" style="margin-left:8px">
            按角色统一配置菜单功能与文档权限
          </el-tag>
        </div>
        <div class="toolbar-right">
          <el-button @click="loadCurrentTab" :icon="Refresh">刷新</el-button>
        </div>
      </div>
    </el-card>

    <!-- 角色选择 -->
    <el-card shadow="never" class="role-select-card">
      <div class="role-select-bar">
        <span style="font-weight:600;font-size:14px;white-space:nowrap">选择角色：</span>
        <el-select
          v-model="selectedRoleId"
          placeholder="请选择一个角色进行权限设置"
          size="large"
          style="width:320px"
          @change="onRoleChange"
        >
          <el-option
            v-for="r in roles"
            :key="r.id"
            :label="r.name"
            :value="r.id"
          >
            <span>{{ r.name }}</span>
            <span style="font-size:12px;color:#86909c;margin-left:8px">{{ r.code }}</span>
          </el-option>
        </el-select>
        <el-tag v-if="selectedRoleId" type="success" effect="light" style="margin-left:12px">
          已选 {{ selectedRole?.name }}
        </el-tag>
        <el-tag v-else type="info" effect="plain" style="margin-left:12px">
          请选择角色后设置权限
        </el-tag>
      </div>
    </el-card>

    <!-- 权限标签页 -->
    <el-card shadow="never" class="tabs-card" v-loading="loading">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane
          v-for="tab in availableTabs"
          :key="tab.name"
          :label="tab.label"
          :name="tab.name"
        >
          <!-- 菜单功能权限 -->
          <div v-if="tab.name === 'menu' && selectedRoleId" class="menu-perm-panel">
            <div class="panel-header">
              <div class="panel-tips">
                <el-tag size="small" type="info">带「默认」标签的为业务角色自动继承权限，可自由修改，保存后将变为显式权限</el-tag>
              </div>
              <el-button type="primary" :loading="menuSaving" :icon="Plus" @click="saveMenuPermissions">
                保存菜单功能权限
              </el-button>
            </div>

            <div class="menu-tree-wrapper">
              <el-tree
                :data="menuTree"
                node-key="code"
                default-expand-all
                :expand-on-click-node="false"
                :props="{ label: 'name', children: 'children' }"
              >
                <template #default="{ node, data }">
                  <div class="menu-tree-node">
                    <div class="node-info">
                      <span class="node-name">{{ node.label }}</span>
                      <el-tag v-if="data.type === 'menu'" size="small" type="info" effect="plain">菜单</el-tag>
                      <el-tag v-else size="small" type="warning" effect="plain">功能</el-tag>
                    </div>
                    <div class="node-action">
                      <el-tag
                        v-if="isInheritedPermission(data.code)"
                        size="small"
                        type="success"
                        effect="plain"
                        class="default-tag"
                      >默认</el-tag>
                      <el-checkbox
                        :model-value="isMenuPermissionChecked(data.code)"
                        size="small"
                        @update:model-value="(val) => toggleMenuPermission(data.code, val)"
                      />
                    </div>
                  </div>
                </template>
              </el-tree>
            </div>
          </div>
          <el-empty v-if="tab.name === 'menu' && !selectedRoleId" description="请先在上方选择一个角色" />

          <!-- 文档权限 -->
          <div v-if="tab.name === 'doc' && selectedRoleId && categories.length > 0" class="doc-perm-panel">
            <div class="panel-header">
              <div class="panel-tips">
                <span>共 {{ totalDocCount }} 个文档，{{ selectedDocCount }} 个已授权</span>
              </div>
              <el-button type="primary" :loading="docSaving" :icon="Plus" @click="handleSaveDocPermissions">
                保存文档权限
              </el-button>
            </div>

            <div class="matrix-scroll">
              <table class="perm-table">
                <thead>
                  <tr>
                    <th class="col-file">
                      <div class="th-file-header">
                        <span>文件列表</span>
                        <span class="th-count">{{ totalDocCount }} 个文档</span>
                      </div>
                    </th>
                    <th class="col-perm">预览</th>
                    <th class="col-perm">下载</th>
                    <th class="col-perm">编辑</th>
                    <th class="col-perm">删除</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="cat in categories" :key="cat.id ?? 'uncat'">
                    <!-- 分类行（带全选复选框+折叠） -->
                    <tr class="tr-category">
                      <td class="td-category">
                        <div class="cat-row">
                          <el-icon class="cat-toggle-icon" @click.stop="toggleCat(cat)">
                            <ArrowDown v-if="cat.expanded !== false" />
                            <ArrowRight v-else />
                          </el-icon>
                          <span class="cat-name" @click.stop="toggleCat(cat)">{{ cat.name }}</span>
                          <span class="cat-count">{{ cat.documents.length }} 个文档</span>
                        </div>
                      </td>
                      <td class="td-check-cat">
                        <el-checkbox
                          :model-value="catPermAll(cat, 'can_view')"
                          :indeterminate="catPermIndeterminate(cat, 'can_view')"
                          size="small"
                          @update:model-value="(val) => catPermAllToggle(cat, 'can_view', val)"
                        />
                      </td>
                      <td class="td-check-cat">
                        <el-checkbox
                          :model-value="catPermAll(cat, 'can_download')"
                          :indeterminate="catPermIndeterminate(cat, 'can_download')"
                          size="small"
                          @update:model-value="(val) => catPermAllToggle(cat, 'can_download', val)"
                        />
                      </td>
                      <td class="td-check-cat">
                        <el-checkbox
                          :model-value="catPermAll(cat, 'can_edit')"
                          :indeterminate="catPermIndeterminate(cat, 'can_edit')"
                          size="small"
                          @update:model-value="(val) => catPermAllToggle(cat, 'can_edit', val)"
                        />
                      </td>
                      <td class="td-check-cat">
                        <el-checkbox
                          :model-value="catPermAll(cat, 'can_print')"
                          :indeterminate="catPermIndeterminate(cat, 'can_print')"
                          size="small"
                          @update:model-value="(val) => catPermAllToggle(cat, 'can_print', val)"
                        />
                      </td>
                    </tr>
                    <!-- 文档行 -->
                    <tr v-for="doc in cat.documents" :key="doc.id" v-show="cat.expanded !== false" class="tr-doc">
                      <td class="td-doc">
                        <div class="doc-row">
                          <span class="doc-indent"></span>
                          <span class="doc-title" :title="doc.title">{{ doc.title }}</span>
                          <span class="doc-no">{{ doc.doc_no }}</span>
                        </div>
                      </td>
                      <td class="td-check">
                        <el-checkbox
                          :model-value="getPermVal(doc.id, 'can_view')"
                          size="small"
                          @update:model-value="(val) => setPerm(doc.id, 'can_view', val)"
                        />
                      </td>
                      <td class="td-check">
                        <el-checkbox
                          :model-value="getPermVal(doc.id, 'can_download')"
                          size="small"
                          @update:model-value="(val) => setPerm(doc.id, 'can_download', val)"
                        />
                      </td>
                      <td class="td-check">
                        <el-checkbox
                          :model-value="getPermVal(doc.id, 'can_edit')"
                          size="small"
                          @update:model-value="(val) => setPerm(doc.id, 'can_edit', val)"
                        />
                      </td>
                      <td class="td-check">
                        <el-checkbox
                          :model-value="getPermVal(doc.id, 'can_print')"
                          size="small"
                          @update:model-value="(val) => setPerm(doc.id, 'can_print', val)"
                        />
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
          <el-empty v-if="tab.name === 'doc' && !loading && !selectedRoleId" description="请先在上方选择一个角色" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Refresh, Plus, ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { hasPermission } from '../utils/permission.js'
import {
  getMenuTree,
  getRoleMenuPermissions,
  saveRoleMenuPermissions,
  getPermissionMatrix,
  savePermissionMatrix
} from '../api/permission.js'

const loading = ref(false)
const menuSaving = ref(false)
const docSaving = ref(false)

// 用户权限判断（控制 Tab 可见性）
const canManageMenuPerms = computed(() => hasPermission('manage_menu_permissions') || hasPermission('manage_system'))
const canManageDocPerms = computed(() => hasPermission('manage_doc_permissions') || hasPermission('manage_system') || hasPermission('assign_roles'))

// 当前可访问的 Tab 列表
const availableTabs = computed(() => {
  const tabs = []
  if (canManageMenuPerms.value) tabs.push({ name: 'menu', label: '菜单功能权限' })
  if (canManageDocPerms.value) tabs.push({ name: 'doc', label: '文档权限' })
  return tabs
})

// 默认选中第一个可用 Tab
const activeTab = ref('menu')

// 监听可用 Tab 变化，确保当前选中的 Tab 仍然可用
watch(availableTabs, (tabs) => {
  if (tabs.length > 0 && !tabs.find(t => t.name === activeTab.value)) {
    activeTab.value = tabs[0].name
  }
}, { immediate: true })

// 角色数据
const roles = ref([])
const selectedRoleId = ref(null)
const selectedRole = computed(() => roles.value.find(r => r.id === selectedRoleId.value))

// ── 菜单功能权限数据 ──
const menuTree = ref([])
const grantedMenuPerms = ref([]) // 显式授予的权限
const inheritedMenuPerms = ref([]) // 业务角色默认继承的权限
const menuPermVersion = ref(0)

// 菜单权限变更追踪（包含显式+继承的显示状态）
const menuCheckedCodes = reactive(new Set())

// ── 文档权限数据 ──
const categories = ref([])
// 权限数据（扁平化）：仅缓存当前选中角色的权限
const rolePerms = reactive({})
const docChangedSet = reactive(new Set())

// 统计当前角色有权限的文档数
const selectedDocCount = computed(() => {
  return Object.values(rolePerms).filter(p => p.can_view || p.can_download || p.can_edit || p.can_print).length
})

const totalDocCount = computed(() => {
  return categories.value.reduce((s, c) => s + c.documents.length, 0)
})

// ── 通用方法 ──

function onRoleChange() {
  loadCurrentTab()
}

function onTabChange() {
  loadCurrentTab()
}

async function loadCurrentTab() {
  if (!selectedRoleId.value) {
    return
  }
  if (activeTab.value === 'menu') {
    await loadMenuPermissions()
  } else {
    await loadDocPermissions()
  }
}

// ── 菜单功能权限方法 ──

async function loadMenuPermissions() {
  loading.value = true
  try {
    // 同时加载菜单树和角色权限
    const [treeRes, roleRes] = await Promise.all([
      getMenuTree(),
      getRoleMenuPermissions(selectedRoleId.value)
    ])
    menuTree.value = treeRes.tree || []
    grantedMenuPerms.value = roleRes.granted_permissions || []
    inheritedMenuPerms.value = roleRes.inherited_permissions || []
    menuPermVersion.value = roleRes.permission_version || 0

    // 初始化勾选状态：显式 + 继承
    menuCheckedCodes.clear()
    for (const code of grantedMenuPerms.value) menuCheckedCodes.add(code)
    for (const code of inheritedMenuPerms.value) menuCheckedCodes.add(code)
  } catch {
    ElMessage.error('加载菜单功能权限失败')
  } finally {
    loading.value = false
  }
}

function isMenuPermissionChecked(code) {
  return menuCheckedCodes.has(code)
}

function isInheritedPermission(code) {
  return inheritedMenuPerms.value.includes(code)
}

function toggleMenuPermission(code, val) {
  if (val) {
    menuCheckedCodes.add(code)
  } else {
    menuCheckedCodes.delete(code)
  }
}

async function saveMenuPermissions() {
  if (!selectedRoleId.value) {
    ElMessage.info('请先选择角色')
    return
  }
  menuSaving.value = true
  try {
    // 提交所有勾选的权限（含已变更为显式的继承权限）
    const explicitCodes = Array.from(menuCheckedCodes)
    await saveRoleMenuPermissions({
      role_id: selectedRoleId.value,
      permission_codes: explicitCodes,
      expected_version: menuPermVersion.value
    })
    ElMessage.success('菜单功能权限保存成功')
    await loadMenuPermissions()
  } catch (e) {
    if (e?.response?.status === 409) {
      ElMessage.warning(e.response.data?.detail || '该角色权限已被他人修改，请刷新后重试')
    } else {
      ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message || '网络错误'))
    }
  } finally {
    menuSaving.value = false
  }
}

// ── 文档权限方法 ──

function getPermVal(docId, field) {
  return rolePerms[docId]?.[field] ?? false
}

function setPerm(docId, field, val) {
  if (!rolePerms[docId]) {
    rolePerms[docId] = reactive({ can_view: false, can_download: false, can_edit: false, can_print: false })
  }
  rolePerms[docId][field] = val
  docChangedSet.add(docId)
}

function catPermAll(cat, field) {
  return cat.documents.length > 0 && cat.documents.every(d => getPermVal(d.id, field))
}

function catPermIndeterminate(cat, field) {
  if (cat.documents.length === 0) return false
  const checked = cat.documents.filter(d => getPermVal(d.id, field)).length
  return checked > 0 && checked < cat.documents.length
}

function catPermAllToggle(cat, field, val) {
  for (const d of cat.documents) {
    if (!rolePerms[d.id]) {
      rolePerms[d.id] = reactive({ can_view: false, can_download: false, can_edit: false, can_print: false })
    }
    rolePerms[d.id][field] = val
    docChangedSet.add(d.id)
  }
}

function toggleCat(cat) {
  cat.expanded = !cat.expanded
}

async function loadDocPermissions() {
  loading.value = true
  try {
    const data = await getPermissionMatrix(selectedRoleId.value)
    roles.value = data.roles || roles.value
    categories.value = (data.categories || []).map(cat => ({ ...cat, expanded: true }))

    // 清空并重建当前角色权限
    Object.keys(rolePerms).forEach(k => delete rolePerms[k])
    docChangedSet.clear()

    for (const cat of categories.value) {
      for (const d of cat.documents) {
        // 后端返回的权限字段直接在文档对象上（扁平结构）
        if (d.can_view || d.can_download || d.can_edit || d.can_print) {
          rolePerms[d.id] = reactive({
            can_view: d.can_view ?? false,
            can_download: d.can_download ?? false,
            can_edit: d.can_edit ?? false,
            can_print: d.can_print ?? false
          })
        }
      }
    }
  } catch {
    ElMessage.error('加载文档权限失败')
  } finally {
    loading.value = false
  }
}

async function handleSaveDocPermissions() {
  if (docChangedSet.size === 0 || !selectedRoleId.value) {
    ElMessage.info('没有需要保存的变更')
    return
  }
  docSaving.value = true
  try {
    const entries = []
    for (const docId of docChangedSet) {
      const p = rolePerms[docId]
      if (!p) continue
      entries.push({
        doc_id: Number(docId),
        role_id: selectedRoleId.value,
        can_view: p.can_view,
        can_download: p.can_download,
        can_edit: p.can_edit,
        can_print: p.can_print
      })
    }
    await savePermissionMatrix({ role_id: selectedRoleId.value, entries })
    ElMessage.success(`已保存 ${entries.length} 条权限变更`)
    docChangedSet.clear()
    await loadDocPermissions()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message || '网络错误'))
  } finally {
    docSaving.value = false
  }
}

onMounted(async () => {
  // 初始加载：先获取角色列表（不需要特定权限）
  loading.value = true
  try {
    const data = await getPermissionMatrix() // 不传 role_id，只拿角色列表
    roles.value = data.roles || []
    if (roles.value.length > 0 && !selectedRoleId.value) {
      selectedRoleId.value = roles.value[0].id
      // 根据当前选中的 Tab 加载对应数据
      await loadCurrentTab()
    }
  } catch (e) {
    // 如果获取角色列表失败，尝试根据权限直接加载当前 Tab
    if (activeTab.value === 'menu' && canManageMenuPerms.value) {
      // 菜单权限 Tab 需要角色列表，但如果失败至少显示空状态
      ElMessage.warning('加载角色列表失败，请手动选择角色')
    } else if (activeTab.value === 'doc' && canManageDocPerms.value) {
      ElMessage.error('加载角色列表失败')
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.perm-matrix { display: flex; flex-direction: column; gap: 16px; }

.toolbar-card, .role-select-card, .tabs-card { border-radius: 8px; }

.toolbar {
  display: flex; justify-content: space-between; align-items: center;
}
.toolbar-left, .toolbar-right {
  display: flex; align-items: center; gap: 8px;
}

.role-select-card .role-select-bar {
  display: flex; align-items: center; gap: 4px;
}

.tabs-card {
  overflow: hidden;
}

/* ── 菜单功能权限面板 ── */
.menu-perm-panel {
  display: flex; flex-direction: column; gap: 16px;
}
.panel-header {
  display: flex; justify-content: space-between; align-items: center;
}
.panel-tips {
  display: flex; align-items: center; gap: 8px;
}

.menu-tree-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px;
  max-height: calc(100vh - 340px);
  overflow-y: auto;
}

.menu-tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 4px 0;
}
.node-info {
  display: flex; align-items: center; gap: 8px;
}
.node-name {
  font-size: 14px; color: #1d2129;
}
.node-action {
  display: flex; align-items: center; gap: 8px;
}
.default-tag {
  margin-right: 4px;
}

/* ── 文档权限面板 ── */
.doc-perm-panel {
  display: flex; flex-direction: column; gap: 16px;
}
.matrix-scroll {
  overflow-x: auto;
  max-height: calc(100vh - 360px);
  overflow-y: auto;
}

/* ── 表格 ── */
.perm-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 600px;
  font-size: 13px;
}
.perm-table th, .perm-table td {
  border: 1px solid #e5e6eb;
  padding: 0;
  text-align: center;
  white-space: nowrap;
}

/* ── 表头 ── */
.col-file {
  background: #f7f8fa;
  text-align: left;
  padding: 10px 12px !important;
  min-width: 260px;
}
.th-file-header {
  display: flex; flex-direction: column; gap: 2px;
}
.th-file-header .th-count {
  font-size: 11px; color: #86909c; font-weight: 400;
}
.col-perm {
  min-width: 60px;
  width: 60px;
  background: #f7f8fa;
  font-size: 12px; font-weight: 500; color: #4e5969;
  padding: 8px 0 !important;
}

/* ── 分类行 ── */
.tr-category td {
  background: #f5f7fa;
  padding: 6px 12px !important;
  border-bottom: 2px solid #e5e6eb;
}
.tr-category { user-select: none; }
.tr-category:hover td { background: #eef1f6 !important; }
.cat-row {
  display: flex; align-items: center; gap: 6px;
}
.cat-toggle-icon, .cat-name {
  cursor: pointer;
}
.cat-toggle-icon {
  font-size: 14px;
  color: #4e5969;
  transition: transform 0.2s;
}
.cat-name { font-weight: 600; font-size: 13px; color: #1d2129; }
.cat-name:hover { color: #165dff; }
.cat-count { font-size: 11px; color: #86909c; font-weight: 400; }
.td-check-cat {
  background: #f5f7fa !important;
  padding: 6px 0 !important;
  border-bottom: 2px solid #e5e6eb;
}

/* ── 文档行 ── */
.tr-doc:hover { background: #f0f5ff; }
.td-doc {
  text-align: left;
  padding: 6px 12px !important;
}
.doc-row {
  display: flex; align-items: center; gap: 8px;
}
.doc-title {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 220px; font-size: 13px;
}
.doc-no { font-size: 11px; color: #c9cdd4; flex-shrink: 0; }
.doc-indent {
  display: inline-block;
  width: 18px;
  flex-shrink: 0;
}
.td-check {
  padding: 4px 0 !important;
}
.td-check:hover { background: #e6f0ff; }
</style>
