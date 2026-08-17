import { describe, it, expect, beforeEach } from 'vitest'
import { hasPermission, ROLES, getMenuKeyByPermission } from './permission.js'

describe('permission.js', () => {
  beforeEach(() => {
    // 每个测试前清空 localStorage，避免相互影响
    localStorage.clear()
  })

  describe('hasPermission', () => {
    it('当用户拥有指定权限时应返回 true', () => {
      localStorage.setItem(
        'user_info',
        JSON.stringify({ permissions: ['upload_doc', 'view_doc_list'] })
      )
      expect(hasPermission('upload_doc')).toBe(true)
    })

    it('当用户未拥有指定权限时应返回 false', () => {
      localStorage.setItem(
        'user_info',
        JSON.stringify({ permissions: ['view_doc_list'] })
      )
      expect(hasPermission('upload_doc')).toBe(false)
    })

    it('当 localStorage 为空时应返回 false 且不抛错', () => {
      expect(() => hasPermission('upload_doc')).not.toThrow()
      expect(hasPermission('upload_doc')).toBe(false)
    })

    it('当 localStorage 中数据不是合法 JSON 时应返回 false 且不抛错', () => {
      localStorage.setItem('user_info', 'not-valid-json')
      expect(() => hasPermission('upload_doc')).not.toThrow()
      expect(hasPermission('upload_doc')).toBe(false)
    })

    it('当 user_info 中 permissions 不是数组时应返回 false', () => {
      localStorage.setItem('user_info', JSON.stringify({ permissions: 'admin' }))
      expect(hasPermission('upload_doc')).toBe(false)
    })
  })

  describe('ROLES', () => {
    it('应导出常用角色名常量', () => {
      expect(ROLES.SUPER_ADMIN).toBe('系统管理员')
      expect(ROLES.DOC_ADMIN).toBe('文档管理员')
      expect(ROLES.DEPT_ADMIN).toBe('部门管理员')
      expect(ROLES.NORMAL_USER).toBe('普通用户')
    })
  })

  describe('getMenuKeyByPermission', () => {
    it('应根据权限码返回对应菜单 key', () => {
      expect(getMenuKeyByPermission('view_doc_list')).toBe('document')
      expect(getMenuKeyByPermission('manage_users')).toBe('user')
      expect(getMenuKeyByPermission('manage_system')).toBe('settings')
    })

    it('未知权限应返回 undefined', () => {
      expect(getMenuKeyByPermission('unknown_permission')).toBeUndefined()
    })
  })
})
