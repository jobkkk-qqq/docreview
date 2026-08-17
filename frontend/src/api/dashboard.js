/**
 * 仪表盘 API
 * 包含统计数据、最近文档等接口
 */
import request from './request.js'

/**
 * 获取仪表盘统计数据
 * @returns {Promise} - { total_docs, month_new, categories, users }
 */
export function getDashboardStats() {
  return request.get('/dashboard/overview')
}

/**
 * 获取最近上传的文档列表
 * @param {Object} params - { limit }
 * @returns {Promise}
 */
export function getRecentDocuments(params) {
  return request.get('/dashboard/recent-documents', { params })
}
