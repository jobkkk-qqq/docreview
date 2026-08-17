/**
 * 权限判断工具函数
 * 根据用户权限列表判断是否有权限访问指定菜单或功能
 */

// 角色名常量（兼容旧代码中按角色名判断的逻辑）
export const ROLES = {
  SUPER_ADMIN: '系统管理员',
  DOC_ADMIN: '文档管理员',
  DEPT_ADMIN: '部门管理员',
  NORMAL_USER: '普通用户'
}

// 菜单-功能树缓存（由 auth store 在获取用户信息时写入）
let menuTreeCache = []

/**
 * 设置菜单功能树缓存
 * @param {Array} tree - 后端 /permissions/menu-tree 返回的 tree
 */
export function setMenuTree(tree) {
  menuTreeCache = tree || []
}

/**
 * 获取菜单功能树缓存
 */
export function getMenuTreeCache() {
  return menuTreeCache
}

/**
 * 根据 menu_key 查找对应菜单节点所需的权限 code
 * 只返回 type='menu' 的节点 code（功能点由具体接口/按钮单独判断）
 */
function findMenuPermissionCodes(menuKey) {
  if (!menuTreeCache.length || !menuKey) return []
  const codes = []
  for (const node of menuTreeCache) {
    if (node.type === 'menu' && node.menu_key === menuKey) {
      codes.push(node.code)
    }
  }
  return codes
}

export function hasPermission(permissionCode) {
  try {
    const raw = localStorage.getItem('user_info')
    if (!raw) return false
    const userInfo = JSON.parse(raw)
    const permissions = userInfo.permissions
    if (!Array.isArray(permissions)) return false
    return permissions.includes(permissionCode)
  } catch (e) {
    return false
  }
}

/**
 * 判断是否有指定菜单的访问权限
 * 优先使用动态菜单树映射；若树未加载则回退到硬编码兜底映射
 */
export function hasMenuPermission(menuKey) {
  let requiredPerms = findMenuPermissionCodes(menuKey)

  // 兜底映射：保证菜单树加载前也能正常工作
  const fallback = {
    dashboard: ['view_dashboard'],
    document: ['view_doc_list'],
    document_upload: ['upload_doc'],
    category: ['manage_categories'],
    user: ['manage_users'],
    department: ['manage_departments'],
    role: ['assign_roles'],
    permission_matrix: ['manage_doc_permissions', 'manage_menu_permissions'],
    log: ['view_audit_logs'],
    settings: ['manage_system']
  }
  if (!requiredPerms.length) {
    requiredPerms = fallback[menuKey] || []
  } else {
    // 菜单树已加载时也合并兜底映射权限码（树中code可能不是实际权限码）
    const fallbackPerms = fallback[menuKey] || []
    requiredPerms = [...new Set([...requiredPerms, ...fallbackPerms])]
  }

  if (!requiredPerms.length) return true
  return requiredPerms.some(p => hasPermission(p))
}

/**
 * 判断当前用户是否为超级管理员
 */
export function isSuperAdmin() {
  try {
    const raw = localStorage.getItem('user_info')
    if (!raw) return false
    const userInfo = JSON.parse(raw)
    return userInfo.is_superuser === true
  } catch (e) {
    return false
  }
}

/**
 * 根据权限 code 查找对应菜单 key
 * 若该权限是菜单节点，返回其 menu_key；
 * 若是功能节点，向上查找父菜单节点返回 menu_key。
 * @param {string} permissionCode - 权限 code
 * @returns {string|undefined} 菜单 key
 */
export function getMenuKeyByPermission(permissionCode) {
  if (!permissionCode) return undefined

  // 兜底映射：保证菜单树加载前也能正常工作
  const fallback = {
    view_dashboard: 'dashboard',
    view_doc_list: 'document',
    view_doc_detail: 'document',
    upload_doc: 'document',
    modify_doc: 'document',
    delete_doc: 'document',
    print_doc: 'document',
    download_doc: 'document',
    manage_doc_permissions: 'document',
    document_upload: 'document_upload',
    manage_categories: 'category',
    manage_users: 'user',
    manage_departments: 'department',
    assign_roles: 'role',
    permission_matrix: 'permission_matrix',
    manage_menu_permissions: 'permission_matrix',
    view_audit_logs: 'log',
    manage_system: 'settings'
  }
  if (fallback[permissionCode]) {
    return fallback[permissionCode]
  }

  if (!menuTreeCache.length) return undefined

  // 先找直接匹配的菜单节点
  for (const node of menuTreeCache) {
    if (node.code === permissionCode && node.type === 'menu') {
      return node.menu_key
    }
  }

  // 再找功能节点，返回父菜单的 menu_key
  for (const node of menuTreeCache) {
    if (node.code === permissionCode && node.type === 'function') {
      const parent = menuTreeCache.find(n => n.code === node.parent_code && n.type === 'menu')
      return parent ? parent.menu_key : undefined
    }
  }

  return undefined
}

/**
 * 从菜单功能树生成前端可见菜单列表
 * @param {Array} permissions - 用户权限 code 列表
 * @returns {Array} 可见的菜单节点列表（仅 type='menu'）
 */
export function buildVisibleMenus(permissions) {
  const perms = new Set(permissions || [])
  const visible = []

  for (const node of menuTreeCache) {
    if (node.type !== 'menu') continue
    // 超级管理员或拥有菜单对应权限即可见
    if (perms.has(node.code) || isSuperAdmin()) {
      visible.push(node)
    }
  }

  return visible.sort((a, b) => (a.sort || 0) - (b.sort || 0))
}

export function canUploadDoc() {
  return hasPermission('upload_doc')
}

export function canModifyDoc() {
  return hasPermission('modify_doc')
}

export function canDeleteDoc() {
  return hasPermission('delete_doc')
}

export function canManageDocPermissions() {
  return hasPermission('manage_doc_permissions')
}

export function canManageUsers() {
  return hasPermission('manage_users')
}

export function canManageRoles() {
  return hasPermission('assign_roles')
}

export function canManageCategories() {
  return hasPermission('manage_categories')
}

export function canManageDepartments() {
  return hasPermission('manage_departments')
}

export function canViewDashboard() {
  return hasPermission('view_dashboard')
}

export function canViewAuditLogs() {
  return hasPermission('view_audit_logs')
}

export function canManageMenuPermissions() {
  return hasPermission('manage_menu_permissions')
}

// 兼容旧命名，保留别名
export const canUpload = canUploadDoc
export const canModify = canModifyDoc
export const canDelete = canDeleteDoc
