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
 * 获取分类目录树（嵌套结构，含每个节点的文档数与子树文档数）
 * 仅分类管理员可用
 * @returns {Promise}
 */
export function getCategoryTree() {
  return request.get('/categories/tree')
}

/**
 * 获取简化分类列表（所有登录用户可访问，用于文档管理侧边栏、上传时选择）
 * 返回 { items: 平铺列表, tree: 嵌套树, uncategorized_count: 未分类文档数 }
 * @returns {Promise}
 */
export function getCategoryListSimple() {
  return request.get('/categories/simple')
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
