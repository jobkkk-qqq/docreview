<template>
  <el-container class="layout-container">
    <!-- PC 端左侧导航 -->
    <el-aside
      v-if="!isMobile"
      :width="appStore.sidebarCollapsed ? '64px' : '220px'"
      class="layout-aside"
    >
      <Sidebar />
    </el-aside>

    <!-- 右侧区域 -->
    <div class="layout-right">
      <!-- 顶部栏 -->
      <el-header height="56px" class="layout-header">
        <div class="header-left">
          <!-- PC 端折叠按钮 -->
          <el-icon
            v-if="!isMobile"
            class="collapse-btn"
            @click="appStore.toggleSidebar"
          >
            <Expand v-if="appStore.sidebarCollapsed" />
            <Fold v-else />
          </el-icon>

          <!-- 移动端菜单按钮 -->
          <el-icon v-else class="mobile-menu-btn" @click="drawerVisible = true">
            <Menu />
          </el-icon>

          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta?.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-icon style="font-size:18px;color:#165dff"><UserFilled /></el-icon>
              <span style="font-weight:500">{{ authStore.userInfo?.display_name || authStore.username || '用户' }}</span>
              <el-icon style="font-size:12px"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人信息
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon> 修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon style="color:#f56c6c"><SwitchButton /></el-icon>
                  <span style="color:#f56c6c">退出登录</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </div>

    <!-- 移动端抽屉式侧边栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      :with-header="false"
      direction="ltr"
      size="220px"
      class="mobile-sidebar-drawer"
    >
      <Sidebar @menu-click="drawerVisible = false" />
    </el-drawer>

    <!-- 修改密码弹窗 -->
    <el-dialog
      v-model="pwdDialogVisible"
      title="修改密码"
      width="420px"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="resetPwdForm"
    >
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="90px"
        @submit.prevent
      >
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input
            v-model="pwdForm.oldPassword"
            type="password"
            show-password
            placeholder="请输入当前密码"
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="pwdForm.newPassword"
            type="password"
            show-password
            placeholder="至少 6 位"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="pwdForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            autocomplete="new-password"
            @keyup.enter="submitPassword"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Expand,
  Fold,
  UserFilled,
  ArrowDown,
  User,
  Lock,
  SwitchButton,
  Menu
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'
import { useAppStore } from '../stores/app.js'
import { changePassword } from '../api/auth.js'
import Sidebar from '../components/Sidebar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const currentRoute = computed(() => route)

// 移动端检测
const MOBILE_BREAKPOINT = 768
const isMobile = ref(window.innerWidth <= MOBILE_BREAKPOINT)
const drawerVisible = ref(false)

function handleResize() {
  isMobile.value = window.innerWidth <= MOBILE_BREAKPOINT
  if (!isMobile.value) {
    drawerVisible.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function handleCommand(command) {
  switch (command) {
    case 'profile':
      break
    case 'password':
      openChangePassword()
      break
    case 'logout':
      handleLogout()
      break
  }
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await authStore.logout()
    router.push('/login')
  } catch {
    // 用户取消
  }
}

// ── 修改密码 ─────────────────────────────────────────────
const pwdDialogVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdFormRef = ref(null)
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const pwdRules = {
  oldPassword: [
    { required: true, message: '请输入旧密码', trigger: 'blur' },
    { min: 6, message: '旧密码至少 6 位', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 128, message: '新密码长度需为 6-128 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.newPassword) {
          callback(new Error('两次输入的新密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function openChangePassword() {
  resetPwdForm()
  pwdDialogVisible.value = true
}

function resetPwdForm() {
  pwdForm.oldPassword = ''
  pwdForm.newPassword = ''
  pwdForm.confirmPassword = ''
  pwdFormRef.value?.clearValidate()
}

async function submitPassword() {
  if (!pwdFormRef.value) return
  try {
    await pwdFormRef.value.validate()
  } catch {
    return
  }
  pwdSubmitting.value = true
  try {
    await changePassword({
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword
    })
    ElMessage.success('密码修改成功，请使用新密码重新登录')
    pwdDialogVisible.value = false
    await authStore.logout()
    router.push('/login')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '密码修改失败')
  } finally {
    pwdSubmitting.value = false
  }
}
</script>
