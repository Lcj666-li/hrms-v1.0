<template>
  <!-- 根组件承载路由页面；登录后额外挂一个全局 AI 助手抽屉。 -->
  <router-view />
  <AiAssistant v-if="userStore.isLoggedIn" />
</template>

<script setup lang="ts">
import AiAssistant from '@/components/AiAssistant.vue'
import { useUserStore } from '@/store/user'

// 只在已登录时显示 AI 入口：Agent 需要 JWT 才能判断角色与权限。
const userStore = useUserStore()
</script>

<style>
* {
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  min-height: 100%;
  margin: 0;
}

body {
  color: #303133;
  font-family:
    "Microsoft YaHei",
    "PingFang SC",
    "Helvetica Neue",
    Arial,
    sans-serif;
  background: #f5f7fa;
}

a {
  color: inherit;
  text-decoration: none;
}
</style>
