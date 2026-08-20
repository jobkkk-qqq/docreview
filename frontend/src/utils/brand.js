/**
 * 系统品牌名称（公司名）统一读取/缓存工具
 * 默认占位为 XXX，部署后由用户在系统配置页设置并保存缓存
 */
const BRAND_KEY = 'brand_name'
// 占位默认值：部署后由用户通过系统配置覆盖为真实公司名
const DEFAULT_BRAND_NAME = 'XXX数字档案管理系统'

export function getBrandName() {
  try {
    return localStorage.getItem(BRAND_KEY) || DEFAULT_BRAND_NAME
  } catch {
    return DEFAULT_BRAND_NAME
  }
}

export function setBrandName(name) {
  try {
    if (name) localStorage.setItem(BRAND_KEY, name)
  } catch {
    // 忽略存储异常
  }
}