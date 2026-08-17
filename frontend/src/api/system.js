/**
 * 系统配置 API
 * 包含系统设置的获取与更新接口
 */
import request from './request.js'

/**
 * 获取系统配置
 * @returns {Promise}
 */
export function getSystemSettings() {
  return request.get('/system/config')
}

/**
 * 获取系统品牌名称（公开接口，无需登录）
 * @returns {Promise<{brand_name: string}>}
 */
export function getSystemBrand() {
  return request.get('/system/brand')
}

/**
 * 更新系统配置
 * @param {Object} data - 配置数据
 * @returns {Promise}
 */
export function updateSystemSettings(data) {
  return request.put('/system/config', data)
}

/**
 * 获取操作日志列表
 * @param {Object} params - 查询参数（分页、筛选等）
 * @returns {Promise}
 */
export function getOperationLogs(params) {
  return request.get('/audit-logs/', { params })
}

/**
 * 获取角色列表（完整信息，含权限与用户数，分页）
 * @param {Object} params - 查询参数（page, page_size）
 * @returns {Promise}
 */
export function getRoleFullList(params) {
  return request.get('/system/roles', { params })
}

/**
 * 获取角色详情
 * @param {number} id - 角色 ID
 * @returns {Promise}
 */
export function getRoleDetail(id) {
  return request.get(`/system/roles/${id}`)
}

/**
 * 创建角色
 * @param {Object} data - 角色信息
 * @returns {Promise}
 */
export function createRole(data) {
  return request.post('/system/roles', data)
}

/**
 * 更新角色
 * @param {number} id - 角色 ID
 * @param {Object} data - 角色信息
 * @returns {Promise}
 */
export function updateRole(id, data) {
  return request.put(`/system/roles/${id}`, data)
}

/**
 * 删除角色
 * @param {number} id - 角色 ID
 * @returns {Promise}
 */
export function deleteRole(id) {
  return request.delete(`/system/roles/${id}`)
}

/**
 * 获取业务范围列表
 * @returns {Promise}
 */
export function getBusinessScopes() {
  return request.get('/system/business-scopes')
}

/**
 * 保存业务范围列表（全量替换）
 * @param {Object} data - { items: [{ code, name }, ...] }
 * @returns {Promise}
 */
export function saveBusinessScopes(data) {
  return request.put('/system/business-scopes', data)
}
