/**
 * 文档相关 API
 * 包含文档的增删改查、上传、下载、审核、预览日志等接口
 */
import request from './request.js'

/**
 * 获取文档级别列表（三级分类：Ⅰ级文件/Ⅱ级文件/Ⅲ级文件/Ⅳ级文件/无级别）
 * @returns {Promise}
 */
export function getDocLevels() {
  return request.get('/system/doc-levels')
}

/**
 * 获取文档列表（扁平分页）
 * @param {Object} params - 查询参数（分页、关键词、分类、部门、文档级别、保密等级等）
 * @returns {Promise}
 */
export function getDocumentList(params) {
  return request.get('/documents/', { params })
}

/**
 * 获取按分类分组的文档列表
 * @param {Object} params - 查询参数（关键词、分类、保密等级等）
 * @returns {Promise} - 返回按分类分组的文档数组
 */
export function getDocumentGrouped(params) {
  return request.get('/documents/grouped', { params })
}

/**
 * 获取文档详情
 * @param {number} id - 文档 ID
 * @returns {Promise}
 */
export function getDocumentDetail(id) {
  return request.get(`/documents/${id}`)
}

/**
 * 上传文档
 * @param {FormData} formData - 包含文件的表单数据
 * @returns {Promise}
 */
export function uploadDocument(formData) {
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 上传超时延长到5分钟，局域网环境传输较慢
  })
}

/**
 * 批量上传文档
 * @param {FormData} formData - 包含多个文件和统一属性的表单数据
 * @returns {Promise}
 */
export function batchUploadDocuments(formData) {
  return request.post('/documents/batch-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 批量上传超时时间延长到5分钟
  })
}

/**
 * 删除文档（软删除，移至回收站）
 * @param {number} id - 文档 ID
 * @returns {Promise}
 */
export function deleteDocument(id) {
  return request.delete(`/documents/${id}`)
}

/**
 * 恢复已删除的文档
 * @param {number} id - 文档 ID
 * @returns {Promise}
 */
export function restoreDocument(id) {
  return request.post(`/documents/${id}/restore`)
}

/**
 * 获取已删除文档列表（管理员）
 * @param {Object} params - { page, page_size, keyword }
 * @returns {Promise}
 */
export function getDeletedDocuments(params) {
  return request.get('/documents/deleted/list', { params })
}

/**
 * 下载文档（返回 blob 数据）
 * @param {number} id - 文档 ID
 * @returns {Promise} - 返回 Blob 数据
 */
export function downloadDocument(id) {
  return request.get(`/documents/${id}/download`, {
    responseType: 'blob'
  })
}

/**
 * 获取文档下载链接
 * @param {number} id - 文档 ID
 * @returns {string}
 */
export function getDocumentDownloadUrl(id) {
  return `/api/documents/${id}/download`
}

/**
 * 上报预览日志
 * @param {number} id - 文档 ID
 * @returns {Promise}
 */
export function reportPreviewLog(id) {
  return request.post(`/documents/${id}/preview`)
}

/**
 * 审核文档
 * @param {number} id - 文档 ID
 * @param {Object} data - { status, comment }
 * @returns {Promise}
 */
export function reviewDocument(id, data) {
  return request.post(`/documents/${id}/review`, data)
}

/**
 * 更新文档信息
 * @param {number} id - 文档 ID
 * @param {Object} data - 更新字段
 * @returns {Promise}
 */
export function updateDocument(id, data) {
  return request.put(`/documents/${id}`, data)
}

// ── 权限管理 ──────────────────────────────────────────

/**
 * 获取文档的权限列表
 * @param {number} docId - 文档 ID
 * @returns {Promise}
 */
export function getDocPermissions(docId) {
  return request.get(`/permissions/documents/${docId}`)
}

/**
 * 授予文档权限
 * @param {number} docId - 文档 ID
 * @param {Object} data - { user_id, can_view, can_download, can_edit }
 * @returns {Promise}
 */
export function grantDocPermission(docId, data) {
  return request.post(`/permissions/documents/${docId}`, data)
}

/**
 * 批量授予文档权限
 * @param {number[]} docIds - 文档 ID 列表
 * @param {Object} data - { user_ids, can_view, can_download, can_edit }
 * @returns {Promise}
 */
export function grantBatchDocPermission(docIds, data) {
  const params = new URLSearchParams()
  docIds.forEach((id) => params.append('doc_ids', id))
  return request.post(`/permissions/documents/batch?${params.toString()}`, data)
}

/**
 * 撤销文档权限
 * @param {number} permId - 权限记录 ID
 * @returns {Promise}
 */
export function revokeDocPermission(permId) {
  return request.delete(`/permissions/documents/${permId}`)
}

/**
 * 获取分类的权限列表
 * @param {number} categoryId - 分类 ID
 * @returns {Promise}
 */
export function getCategoryPermissions(categoryId) {
  return request.get(`/permissions/categories/${categoryId}`)
}

/**
 * 授予分类权限
 * @param {Object} data - { user_id, category_id, can_edit, can_view }
 * @returns {Promise}
 */
export function grantCategoryPermission(data) {
  return request.post('/permissions/categories', data)
}

/**
 * 撤销分类权限
 * @param {number} permId - 权限记录 ID
 * @returns {Promise}
 */
export function revokeCategoryPermission(permId) {
  return request.delete(`/permissions/categories/${permId}`)
}