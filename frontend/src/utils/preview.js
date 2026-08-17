/**
 * 文档预览工具
 * 支持 Word、Excel、PPT、PDF、TXT、图片 格式的在线预览
 */

// Office 文件扩展名集合
export const OFFICE_EXTS = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']

// 图片 MIME 类型映射
export const IMAGE_MIME_MAP = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  webp: 'image/webp',
  bmp: 'image/bmp',
  svg: 'image/svg+xml',
}

// 支持预览的文件类型
const PREVIEWABLE_TYPES = {
  doc: 'word',
  docx: 'word',
  xls: 'excel',
  xlsx: 'excel',
  ppt: 'ppt',
  pptx: 'ppt',
  pdf: 'pdf',
  txt: 'txt',
  md: 'txt',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  webp: 'image',
  bmp: 'image',
  svg: 'image',
}

/**
 * 判断文件类型是否可预览
 * @param {string} fileName - 文件名或文件类型
 * @returns {boolean}
 */
export function isPreviewable(fileName) {
  if (!fileName) return false
  const ext = fileName.split('.').pop().toLowerCase()
  return !!PREVIEWABLE_TYPES[ext]
}

/**
 * 获取文件预览类型
 * @param {string} fileName - 文件名
 * @returns {string|null} preview type: word/excel/ppt/pdf/txt/image
 */
export function getPreviewType(fileName) {
  if (!fileName) return null
  const ext = fileName.split('.').pop().toLowerCase()
  return PREVIEWABLE_TYPES[ext] || null
}

/**
 * 获取预览文件的 blob URL（用于 PDF/TXT/图片 内嵌展示）
 * @param {Blob} blob - 文件 blob 数据
 * @param {string} fileName - 文件名
 * @returns {string} blob URL
 */
export function getPreviewBlobUrl(blob, fileName) {
  const type = getPreviewType(fileName)
  if (type === 'pdf') {
    return URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
  }
  if (type === 'txt') {
    return URL.createObjectURL(new Blob([blob], { type: 'text/plain;charset=utf-8' }))
  }
  if (type === 'image') {
    const ext = fileName.split('.').pop().toLowerCase()
    return URL.createObjectURL(new Blob([blob], { type: IMAGE_MIME_MAP[ext] || 'image/png' }))
  }
  return URL.createObjectURL(blob)
}
