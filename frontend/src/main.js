/**
 * 应用入口文件
 * 注册 ElementPlus、Router、Pinia 等全局插件
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router/index.js'
import './styles/global.css'

// 创建 Vue 实例
const app = createApp(App)

// 注册 Pinia 状态管理
app.use(createPinia())

// 注册 Vue Router
app.use(router)

// 注册 Element Plus（全量引入，中文语言包）
app.use(ElementPlus, {
  locale: zhCn
})

// 挂载应用
app.mount('#app')