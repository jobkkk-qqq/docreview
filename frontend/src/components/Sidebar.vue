<template>
  <div class="sidebar-container">
    <!-- Logo 区域 -->
    <div class="sidebar-logo">
      <el-icon :size="24" color="#409eff"><Document /></el-icon>
      <span v-show="!appStore.sidebarCollapsed" class="logo-text">{{ brandName }}</span>
    </div>

    <!-- 导航菜单 -->
    <el-menu
      :default-active="activeMenu"
      :collapse="appStore.sidebarCollapsed"
      :collapse-transition="false"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
      router
    >
      <template v-for="item in visibleMenus" :key="item.path">
        <!-- 单级菜单 -->
        <el-menu-item :index="item.path" @click="emit('menu-click')">
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup>
/**
 * 左侧导航菜单
 * 根据后端菜单功能树动态渲染菜单项
 */
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer,
  Document,
  Upload,
  FolderOpened,
  User,
  OfficeBuilding,
  UserFilled,
  Tickets,
  Setting,
  Grid
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'
import { useAppStore } from '../stores/app.js'
import { hasMenuPermission } from '../utils/permission.js'
import { getSystemBrand } from '../api/system.js'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

// 品牌名称（从后端公开接口加载）
const brandName = ref('沃迪森数字档案管理系统')

onMounted(async () => {
  try {
    const res = await getSystemBrand()
    if (res && res.brand_name) {
      brandName.value = res.brand_name
    }
  } catch {
    // 加载失败时使用默认名称
  }
})

// 向父组件通知菜单点击事件（移动端抽屉关闭用）
const emit = defineEmits(['menu-click'])

// menu_key -> 路由 path 映射
const MENU_PATH_MAP = {
  dashboard: '/dashboard',
  document: '/documents',
  document_upload: '/documents/upload',
  category: '/categories',
  user: '/users',
  department: '/departments',
  role: '/roles',
  permission_matrix: '/permissions/matrix',
  log: '/logs',
  settings: '/settings'
}

// menu_key -> 图标组件映射
const MENU_ICON_MAP = {
  dashboard: Odometer,
  document: Document,
  document_upload: Upload,
  category: FolderOpened,
  user: User,
  department: OfficeBuilding,
  role: UserFilled,
  permission_matrix: Grid,
  log: Tickets,
  settings: Setting
}

/**
 * 根据后端菜单树和本地权限过滤可见菜单
 */
const visibleMenus = computed(() => {
  const tree = authStore.menuTree || []
  if (!tree.length) {
    // 菜单树尚未加载时，回退到本地硬编码菜单 + hasMenuPermission
    return fallbackMenus.filter(item => hasMenuPermission(item.menuKey))
  }

  const menus = []
  for (const node of tree) {
    if (node.type !== 'menu') continue
    const path = MENU_PATH_MAP[node.menu_key]
    const icon = MENU_ICON_MAP[node.menu_key]
    if (!path) continue
    if (hasMenuPermission(node.menu_key)) {
      menus.push({
        path,
        title: node.name,
        icon: icon || Document,
        menuKey: node.menu_key,
        sort: node.sort || 0
      })
    }
  }
  return menus.sort((a, b) => a.sort - b.sort)
})

// 菜单树加载前的兜底菜单
const fallbackMenus = [
  { path: '/dashboard', title: '仪表盘', icon: Odometer, menuKey: 'dashboard' },
  { path: '/documents', title: '文档管理', icon: Document, menuKey: 'document' },
  { path: '/documents/upload', title: '文档上传', icon: Upload, menuKey: 'document_upload' },
  { path: '/categories', title: '分类管理', icon: FolderOpened, menuKey: 'category' },
  { path: '/users', title: '用户管理', icon: User, menuKey: 'user' },
  { path: '/departments', title: '部门管理', icon: OfficeBuilding, menuKey: 'department' },
  { path: '/roles', title: '角色管理', icon: UserFilled, menuKey: 'role' },
  { path: '/permissions/matrix', title: '权限矩阵', icon: Grid, menuKey: 'permission_matrix' },
  { path: '/logs', title: '操作日志', icon: Tickets, menuKey: 'log' },
  { path: '/settings', title: '系统配置', icon: Setting, menuKey: 'settings' }
]

// 当前激活的菜单路径
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #304156;
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: #263445;
  color: #fff;
  overflow: hidden;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
</style>
