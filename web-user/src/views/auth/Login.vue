<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <img src="@/assets/logo.svg" alt="logo" class="logo" />
        <h1>{{ systemStore.productName }}</h1>
        <p>智能体工作台</p>
      </div>

      <el-tabs v-model="mode" class="login-tabs" stretch>
        <el-tab-pane label="密码登录" name="password" />
        <el-tab-pane label="验证码登录" name="code" />
      </el-tabs>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item v-if="mode === 'password'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item v-else prop="code">
          <div class="code-row">
            <el-input
              v-model="form.code"
              placeholder="请输入验证码"
              size="large"
              :prefix-icon="Key"
            />
            <el-button
              size="large"
              :disabled="countdown > 0"
              :loading="sending"
              @click="handleSendCode"
            >
              {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Lock, Key } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import { sendCode } from '@/api/auth'

// T7 用户侧登录：密码 / 验证码双通道；对接 /v1/customer/auth/*（节点1 裁定 Q1）
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const systemStore = useSystemStore()

const formRef = ref(null)
const mode = ref('password')
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
let timer = null

const form = reactive({
  email: '',
  password: '',
  code: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '验证码为 6 位数字', trigger: 'blur' }
  ]
}

async function handleSendCode() {
  // 仅校验邮箱项，不触发表单整体提交
  try {
    await formRef.value.validateField('email')
  } catch (e) {
    return
  }
  sending.value = true
  try {
    await sendCode({ email: form.email })
    ElMessage.success('验证码已发送，请注意查收')
    countdown.value = 60
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
        timer = null
      }
    }, 1000)
  } catch (e) {
    // 错误提示已由拦截器统一弹出
  } finally {
    sending.value = false
  }
}

async function handleLogin() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  loading.value = true
  try {
    const payload =
      mode.value === 'password'
        ? { email: form.email, password: form.password }
        : { email: form.email, code: form.code }
    await authStore.login(mode.value, payload)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/workflows')
  } catch (e) {
    // 错误提示已由拦截器统一弹出
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  systemStore.loadConfig()
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style scoped lang="scss">
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 36px 36px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 20px;

  .logo {
    width: 56px;
    height: 56px;
  }

  h1 {
    margin-top: 12px;
    font-size: 22px;
    font-weight: 600;
  }

  p {
    margin-top: 4px;
    font-size: 13px;
    color: var(--u-text-sub);
  }
}

.login-tabs {
  margin-bottom: 8px;
}

.code-row {
  display: flex;
  gap: 12px;
  width: 100%;

  .el-input {
    flex: 1;
  }

  .el-button {
    flex-shrink: 0;
    min-width: 120px;
  }
}

.login-btn {
  width: 100%;
}
</style>
