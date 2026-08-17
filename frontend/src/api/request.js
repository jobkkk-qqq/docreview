/**
 * axios 请求封装
 * 统一处理请求拦截（添加 token）和响应拦截（错误处理）
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router/index.js'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器 —— 自动在 Header 添加 Authorization token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 —— 统一错误处理
request.interceptors.response.use(
  (response) => {
    // 直接返回响应数据
    return response.data
  },
  async (error) => {
    if (error.response) {
      const { status, data, config } = error.response

      // 401 未授权 —— 跳转到登录页
      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('user_info')
        router.push('/login')
        return Promise.reject(error)
      }

      // 对于 blob 类型的错误响应，需要解析 JSON 获取错误消息
      let message = ''
      if (data instanceof Blob && data.type && data.type.includes('application/json')) {
        try {
          const text = await data.text()
          const json = JSON.parse(text)
          message = json.detail || json.message || `请求错误 (${status})`
        } catch {
          message = `请求错误 (${status})`
        }
      } else {
        message = data?.detail || data?.message || `请求错误 (${status})`
      }

      // 409 重复文件 —— 不弹全局提示，由调用方自行处理
      if (status === 409) {
        error.errorMessage = typeof data?.detail === 'object' ? data.detail : (data?.detail || '文件重复')
        return Promise.reject(error)
      }

      // 其他错误 —— 显示后端返回的错误信息（预览等场景由调用方自行处理，不弹全局提示）
      if (!(config && config.responseType === 'blob' && status !== 401)) {
        ElMessage.error(message)
      }

      // 将解析后的消息附加到error对象上，方便调用方使用
      error.errorMessage = message
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络连接异常')
    }

    return Promise.reject(error)
  }
)

export default request