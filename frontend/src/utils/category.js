/**
 * 分类显示相关的小工具
 */

/**
 * 分类下拉/选项的显示文案
 *
 * 分类支持多级嵌套后，不同层级下可能有同名分类，
 * 因此有层级时显示完整路径（如「标准表单 / 品质文件」），根分类仍只显示名称。
 *
 * @param {{ name?: string, path?: string, depth?: number } | null} item
 * @returns {string}
 */
export function categoryOptionLabel(item) {
  if (!item) return ''
  if (item.depth && item.depth > 0) return item.path || item.name || ''
  return item.name || ''
}
