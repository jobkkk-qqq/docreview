/**
 * 用户管理 API
 * 包含用户的增删改查、启用/禁用、重置密码等接口
 */
import request from './request.js'

/**
 * 获取用户列表
 * @param {Object} params - 查询参数（分页、关键词、部门、角色等）
 * @returns {Promise}
 */
export function getUserList(params) {
  return request.get('/users/', { params })
}

/**
 * 获取用户详情
 * @param {number} id - 用户 ID
 * @returns {Promise}
 */
export function getUserDetail(id) {
  return request.get(`/users/${id}`)
}

/**
 * 创建用户
 * @param {Object} data - 用户信息
 * @returns {Promise}
 */
export function createUser(data) {
  return request.post('/users/', data)
}

/**
 * 更新用户
 * @param {number} id - 用户 ID
 * @param {Object} data - 用户信息
 * @returns {Promise}
 */
export function updateUser(id, data) {
  return request.put(`/users/${id}`, data)
}

/**
 * 删除用户
 * @param {number} id - 用户 ID
 * @returns {Promise}
 */
export function deleteUser(id) {
  return request.delete(`/users/${id}`)
}

/**
 * 重置用户密码
 * @param {number} id - 用户 ID
 * @param {Object} data - { new_password }
 * @returns {Promise}
 */
export function resetUserPassword(id, data) {
  return request.put(`/users/${id}/reset-password`, data)
}

/**
 * 启用/禁用用户
 * @param {number} id - 用户 ID
 * @param {Object} data - { is_active }
 * @returns {Promise}
 */
export function toggleUserStatus(id, data) {
  return request.put(`/users/${id}/status`, data)
}
