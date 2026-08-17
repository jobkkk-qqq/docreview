<template>
  <div class="login-container">
    <div class="login-box">
      <div class="brand">
        <span class="logo-icon">📋</span>
        <h2>{{ brandName }}</h2>
        <p>DocReview · 文档全生命周期管理</p>
      </div>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="0"
        size="large"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%; height: 44px; font-size: 15px"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'
import { getSystemBrand } from '../api/system.js'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 品牌名称（登录页默认显示，稍后从后端公开接口加载）
const brandName = ref('XXX数字档案管理系统')

onMounted(() => {
  const storedToken = localStorage.getItem('token')
  if (storedToken) {
    localStorage.removeItem('token')
    localStorage.removeItem('user_info')
    authStore.token = ''
    authStore.userInfo = null
  }
  // 加载系统配置的品牌名称
  loadBrandName()
})

async function loadBrandName() {
  try {
    const res = await getSystemBrand()
    if (res && res.brand_name) {
      brandName.value = res.brand_name
    }
  } catch {
    // 加载失败时使用默认名称
  }
}

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await authStore.login(loginForm)
      ElMessage.success('登录成功')
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } catch (error) {
      // 错误已在 request.js 拦截器中处理
    } finally {
      loading.value = false
    }
  })
}
</script>
