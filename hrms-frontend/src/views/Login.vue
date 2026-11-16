<script setup lang="ts">
/**
 * 登录页面。
 *
 * 负责收集用户名和密码、执行表单校验、调用 Pinia 登录、
 * 保存 JWT，并按照后端返回的角色进入对应工作台。
 */

import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

// 提交前先做前端必填校验，减少无意义的登录请求。
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function submitLogin() {
  // validate() 校验失败会 reject；转换成 false 后统一走下面的 return。
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  loading.value = true
  try {
    const result = await userStore.login({
      // 去掉用户名首尾空格，密码保持原样，避免误改用户输入。
      username: form.username.trim(),
      password: form.password,
    })
    const homePath =
      result.user.role === 'manager'
        ? '/manager/dashboard'
        : '/employee/dashboard'
    const redirect = route.query.redirect

    // 只有 redirect 的路径前缀与当前角色匹配时才回到原页面，
    // 防止通过篡改 query 参数跳到另一个角色的路由。
    if (
      typeof redirect === 'string' &&
      redirect.startsWith(
        result.user.role === 'manager' ? '/manager/' : '/employee/',
      )
    ) {
      await router.replace(redirect)
    } else {
      await router.replace(homePath)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="login-intro">
        <div class="brand-mark">H</div>
        <div>
          <h1>人事管理系统</h1>
          <p>Human Resource Management System</p>
        </div>
        <div class="intro-line" />
        <div class="system-code">HRMS / 2026</div>
      </section>

      <section class="login-panel">
        <div class="panel-heading">
          <h2>账号登录</h2>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          @keyup.enter="submitLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              :prefix-icon="User"
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              :prefix-icon="Lock"
              type="password"
              show-password
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="login-button"
            :loading="loading"
            @click="submitLogin"
          >
            登录
          </el-button>
        </el-form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  padding: 24px;
  background: #eef2f6;
  place-items: center;
}

.login-shell {
  display: grid;
  width: min(920px, 100%);
  min-height: 540px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #e1e7ee;
  border-radius: 8px;
  box-shadow: 0 18px 45px rgb(23 43 77 / 10%);
  grid-template-columns: minmax(0, 1fr) 420px;
}

.login-intro {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 44px;
  background: #f8fafc;
  border-right: 1px solid #e7ebf0;
}

.brand-mark {
  display: grid;
  width: 48px;
  height: 48px;
  color: #ffffff;
  font-size: 26px;
  font-weight: 800;
  background: #2563eb;
  border-radius: 8px;
  place-items: center;
}

.login-intro h1 {
  margin: 0 0 10px;
  color: #172033;
  font-size: 34px;
  letter-spacing: 0;
}

.login-intro p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.intro-line {
  width: 64px;
  height: 4px;
  background: #d97706;
  border-radius: 2px;
}

.system-code {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 44px;
}

.panel-heading {
  margin-bottom: 28px;
}

.panel-heading h2 {
  margin: 0;
  color: #172033;
  font-size: 24px;
}

.login-button {
  width: 100%;
  margin-top: 8px;
}

@media (max-width: 760px) {
  .login-page {
    padding: 14px;
  }

  .login-shell {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .login-intro {
    min-height: 190px;
    padding: 28px;
    border-right: 0;
    border-bottom: 1px solid #e7ebf0;
  }

  .login-intro h1 {
    font-size: 28px;
  }

  .intro-line,
  .system-code {
    display: none;
  }

  .login-panel {
    padding: 30px 24px;
  }
}
</style>
