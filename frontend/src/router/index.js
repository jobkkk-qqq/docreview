/**
 * 路由配置
 * 包含登录页、仪表盘、文档管理、用户管理、系统管理等路由
 * 以及路由守卫（未登录跳转登录页，已登录禁止访问登录页）
 */
import { createRouter, createWebHistory } from 'vue-router'

// 路由表
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘', menuKey: 'dashboard' }
      },
      {
        path: 'documents',
        name: 'DocumentManage',
        component: () => import('../views/DocumentManage.vue'),
        meta: { title: '文档管理', menuKey: 'document' }
      },
      {
        path: 'documents/upload',
        name: 'DocumentUpload',
        component: () => import('../views/DocumentUpload.vue'),
        meta: { title: '文档上传', menuKey: 'document_upload' }
      },
      {
        path: 'documents/view',
        name: 'DocumentView',
        component: () => import('../views/DocumentView.vue'),
        meta: { title: '文档查看', menuKey: 'document_view' }
      },
      {
        path: 'categories',
        name: 'CategoryManage',
        component: () => import('../views/CategoryManage.vue'),
        meta: { title: '分类管理', menuKey: 'category' }
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('../views/UserManage.vue'),
        meta: { title: '用户管理', menuKey: 'user' }
      },
      {
        path: 'departments',
        name: 'DepartmentManage',
        component: () => import('../views/DepartmentManage.vue'),
        meta: { title: '部门管理', menuKey: 'department' }
      },
      {
        path: 'roles',
        name: 'RoleManage',
        component: () => import('../views/RoleManage.vue'),
        meta: { title: '角色管理', menuKey: 'role' }
      },
      {
        path: 'permissions/matrix',
        name: 'PermissionMatrix',
        component: () => import('../views/PermissionMatrix.vue'),
        meta: { title: '权限矩阵', menuKey: 'permission_matrix' }
      },
      {
        path: 'logs',
        name: 'OperationLog',
        component: () => import('../views/OperationLog.vue'),
        meta: { title: '操作日志', menuKey: 'log' }
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('../views/SystemSettings.vue'),
        meta: { title: '系统配置', menuKey: 'settings' }
      }
    ]
  },
  // 404 页面
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.public) {
    // 公开页面（如登录页）
    if (token && to.name === 'Login') {
      // 已登录用户禁止访问登录页，重定向到首页
      // 注意：token 可能已过期，如果 API 返回 401 会被拦截器处理
      next({ path: '/' })
    } else {
      // 进入登录页时清除可能过期的旧 token
      if (to.name === 'Login' && token) {
        localStorage.removeItem('token')
        localStorage.removeItem('user_info')
      }
      next()
    }
  } else {
    // 需要认证的页面
    if (!token) {
      // 未登录，跳转到登录页
      next({ path: '/login', query: { redirect: to.fullPath } })
    } else {
      next()
    }
  }

  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - XXX数字档案管理系统`
  }
})

export default router
