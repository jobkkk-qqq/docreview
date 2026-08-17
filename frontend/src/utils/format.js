/**
 * 格式化工具函数
 * 统一日期、文件大小、文件类型、保密等级等格式化逻辑
 */

/**
 * 格式化日期时间
 * @param {string|Date} dateStr - 日期字符串或 Date 对象
 * @param {string} format - 格式模板，默认 'YYYY-MM-DD HH:mm'
 * @returns {string}
 */
export function formatDate(dateStr, format = 'YYYY-MM-DD HH:mm') {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  const pad = (n) => String(n).padStart(2, '0')
  const map = {
    YYYY: d.getFullYear(),
    MM: pad(d.getMonth() + 1),
    DD: pad(d.getDate()),
    HH: pad(d.getHours()),
    mm: pad(d.getMinutes()),
    ss: pad(d.getSeconds()),
  }
  let result = format
  for (const [key, val] of Object.entries(map)) {
    result = result.replace(key, val)
  }
  return result
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(size < 10 && unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`
}

/**
 * 获取文件扩展名（小写）
 * @param {string} filename
 * @returns {string}
 */
export function getFileExt(filename) {
  if (!filename) return ''
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

/**
 * 文件类型标签类型（用于 el-tag type 属性）
 * @param {string} filename
 * @returns {string}
 */
export function fileTypeTagType(filename) {
  const ext = getFileExt(filename)
  const typeMap = {
    pdf: 'danger',
    doc: 'primary', docx: 'primary',
    xls: 'success', xlsx: 'success',
    ppt: 'warning', pptx: 'warning',
    txt: 'info',
    png: '', jpg: '', jpeg: '', gif: '', webp: '', bmp: '', svg: '',
    md: 'info',
  }
  return typeMap[ext] ?? ''
}

/**
 * 保密等级标签类型
 * @param {string} level
 * @returns {string}
 */
export function confidentialityTagType(level) {
  const map = {
    public: 'success',
    internal: '',
    confidential: 'warning',
    top_secret: 'danger',
  }
  return map[level] || 'info'
}

/**
 * 保密等级中文标签
 * @param {string} level
 * @returns {string}
 */
export function confidentialityLabel(level) {
  const map = {
    public: '公开',
    internal: '内部',
    confidential: '机密',
    top_secret: '绝密',
  }
  return map[level] || level || '-'
}
