/**
 * 认证相关 API
 * 包含登录、登出、修改密码等接口
 */
import request from './request.js'

/**
 * 用户登录
 * @param {Object} data - { username, password }
 * @returns {Promise}
 */
export function login(data) {
  return request.post('/auth/login', data)
}

/**
 * 用户登出
 * @returns {Promise}
 */
export function logout() {
  return request.post('/auth/logout')
}

/**
 * 修改密码
 * @param {Object} data - { old_password, new_password }
 * @returns {Promise}
 */
export function changePassword(data) {
  return request.post('/auth/change-password', data)
}

/**
 * 获取当前登录用户信息
 * @returns {Promise}
 */
export function getUserInfo() {
  return request.get('/users/me')
}