/**
 * 分类管理 API
 * 包含文档分类的增删改查接口
 */
import request from './request.js'

/**
 * 获取分类列表
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getCategoryList(params) {
  return request.get('/categories/', { params })
}

/**
 * 获取简化分类列表（所有登录用户可访问，用于上传时选择）
 * @returns {Promise}
 */
export function getCategoryListSimple() {
  return request.get('/categories/simple')
}

/**
 * 获取分类详情
 * @param {number} id - 分类 ID
 * @returns {Promise}
 */
export function getCategoryDetail(id) {
  return request.get(`/categories/${id}`)
}

/**
 * 创建分类
 * @param {Object} data - { name, description, parent_id }
 * @returns {Promise}
 */
export function createCategory(data) {
  return request.post('/categories/', data)
}

/**
 * 更新分类
 * @param {number} id - 分类 ID
 * @param {Object} data - 分类信息
 * @returns {Promise}
 */
export function updateCategory(id, data) {
  return request.put(`/categories/${id}`, data)
}

/**
 * 删除分类
 * @param {number} id - 分类 ID
 * @returns {Promise}
 */
export function deleteCategory(id) {
  return request.delete(`/categories/${id}`)
}
