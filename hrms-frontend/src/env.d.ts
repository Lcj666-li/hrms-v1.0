/// <reference types="vite/client" />

// 让 TypeScript 认识 .vue 单文件组件，否则 import App from './App.vue' 会报类型错误。
declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}

interface ImportMetaEnv {
  // 这两个变量来自 .env 文件，Vite 只会把 VITE_ 开头的变量暴露给前端代码。
  readonly VITE_API_BASE_URL?: string
  readonly VITE_PROXY_TARGET?: string
  // Agent 服务地址（默认 http://127.0.0.1:8010）
  readonly VITE_AGENT_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
