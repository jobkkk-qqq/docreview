/**
 * 用户认证状态管理
 * 管理 token、用户信息、角色等认证相关数据
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, logout as logoutApi, getUserInfo as getUserInfoApi } from '../api/auth.js'
import { getMenuTree } from '../api/permission.js'
import { setMenuTree } from '../utils/permission.js'

export const useAuthStore = defineStore('auth', () => {
  // token
  const token = ref(localStorage.getItem('token') || '')

  // 用户信息
  const userInfo = ref(JSON.parse(localStorage.getItem('user_info') || 'null'))

  // 菜单功能树
  const menuTree = ref([])

  // 如有缓存 token，主动加载菜单功能树
  if (token.value) {
    loadMenuTree()
  }

  // 计算属性 —— 是否已登录
  const isLoggedIn = computed(() => !!token.value)

  // 计算属性 —— 当前用户角色名（兼容旧格式）
  const role = computed(() => userInfo.value?.role?.name || '')

  // 计算属性 —— 当前用户名
  const username = computed(() => userInfo.value?.username || '')

  // 计算属性 —— 用户权限列表
  const permissions = computed(() => userInfo.value?.permissions || [])

  // 计算属性 —— 用户角色名称列表
  const roleNames = computed(() => userInfo.value?.role_names || [])

  /**
   * 登录
   * @param {Object} credentials - { username, password }
   */
  async function login(credentials) {
    const res = await loginApi(credentials)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)

    if (res.user) {
      userInfo.value = res.user
      localStorage.setItem('user_info', JSON.stringify(res.user))
      // 并行加载菜单功能树
      loadMenuTree()
    } else {
      await fetchUserInfo()
    }
  }

  /**
   * 加载菜单功能树到缓存
   */
  async function loadMenuTree() {
    try {
      const res = await getMenuTree()
      const tree = res.tree || []
      menuTree.value = tree
      setMenuTree(tree)
    } catch {
      // 菜单树加载失败不影响主流程
    }
  }

  /**
   * 获取当前用户信息
   */
  async function fetchUserInfo() {
    const res = await getUserInfoApi()
    userInfo.value = res
    localStorage.setItem('user_info', JSON.stringify(res))
    // 同步加载菜单功能树
    await loadMenuTree()
  }

  /**
   * 登出
   */
  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 即使接口报错也执行本地清理
    }
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user_info')
  }

  return {
    token,
    userInfo,
    menuTree,
    isLoggedIn,
    role,
    username,
    permissions,
    roleNames,
    login,
    fetchUserInfo,
    logout
  }
})