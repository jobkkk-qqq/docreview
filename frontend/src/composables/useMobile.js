import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 移动端检测 composable
 * 统一管理移动端断点检测逻辑，避免各组件重复实现
 * @param {number} breakpoint - 移动端断点宽度（像素），默认 768
 * @returns {{ isMobile: import('vue').Ref<boolean> }}
 */
export function useMobile(breakpoint = 768) {
  const isMobile = ref(false)

  function checkMobile() {
    isMobile.value = window.innerWidth <= breakpoint
  }

  onMounted(() => {
    checkMobile()
    window.addEventListener('resize', checkMobile)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', checkMobile)
  })

  return { isMobile }
}
