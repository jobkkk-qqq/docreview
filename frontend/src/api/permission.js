/**
 * 权限管理 API
 * 包含菜单功能树、角色权限、权限矩阵等接口
 */
import request from './request.js'

/**
 * 获取菜单功能树
 * @returns {Promise<{tree: Array}>}
 */
export function getMenuTree() {
  return request.get('/permissions/menu-tree')
}

/**
 * 获取角色的菜单功能权限
 * @param {number} roleId - 角色 ID
 * @returns {Promise}
 */
export function getRoleMenuPermissions(roleId) {
  return request.get('/permissions/role-permissions', { params: { role_id: roleId } })
}

/**
 * 保存角色的菜单功能权限
 * @param {Object} data - { role_id, permission_codes, expected_version }
 * @returns {Promise}
 */
export function saveRoleMenuPermissions(data) {
  return request.put('/permissions/role-permissions', data)
}

/**
 * 获取权限矩阵数据（按角色）
 * @param {number} roleId - 角色 ID
 * @returns {Promise}
 */
export function getPermissionMatrix(roleId) {
  return request.get('/permissions/matrix', { params: { role_id: roleId } })
}

/**
 * 保存权限矩阵数据
 * @param {Object} data - { entries: [...] }
 * @returns {Promise}
 */
export function savePermissionMatrix(data) {
  return request.put('/permissions/matrix', data)
}
