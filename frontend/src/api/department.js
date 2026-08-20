/**
 * 部门管理 API
 * 包含部门的增删改查接口
 */
import request from './request.js'

/**
 * 获取部门简要列表（所有登录用户可访问，用于文档上传/筛选时选择二级分类）
 * @returns {Promise}
 */
export function getDepartmentSimple() {
  return request.get('/departments/simple')
}

/**
 * 获取部门列表
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getDepartmentList(params) {
  return request.get('/departments/', { params })
}

/**
 * 创建部门
 * @param {Object} data - { name, description, parent_id }
 * @returns {Promise}
 */
export function createDepartment(data) {
  return request.post('/departments/', data)
}

/**
 * 更新部门
 * @param {number} id - 部门 ID
 * @param {Object} data - 部门信息
 * @returns {Promise}
 */
export function updateDepartment(id, data) {
  return request.put(`/departments/${id}`, data)
}

/**
 * 删除部门
 * @param {number} id - 部门 ID
 * @returns {Promise}
 */
export function deleteDepartment(id) {
  return request.delete(`/departments/${id}`)
}
