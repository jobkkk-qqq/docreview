/**
 * 角色管理 API
 */
import request from './request.js'

/**
 * 获取角色列表
 * @returns {Promise}
 */
export function getRoleList() {
  return request.get('/users/roles')
}

/**
 * 获取简化角色列表（所有登录用户可访问，用于上传时授权选择）
 * @returns {Promise}
 */
export function getRoleListSimple() {
  return request.get('/users/roles/simple')
}