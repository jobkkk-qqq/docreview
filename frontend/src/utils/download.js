/**
 * 文件下载工具函数
 * 统一处理 Blob 下载逻辑
 */

/**
 * 触发浏览器下载 Blob 文件
 * @param {Blob} blob - 文件 Blob 数据
 * @param {string} filename - 下载文件名
 */
export function saveBlobAsFile(blob, filename) {
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename || 'download'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // 延迟释放 URL，避免下载中断
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
}
