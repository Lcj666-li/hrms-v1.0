import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

/**
 * Vue 应用入口。
 *
 * 执行顺序：创建应用 -> 注册图标 -> 安装 Pinia -> 安装路由 -> 安装 Element Plus -> 挂载。
 */

const app = createApp(App)

// 全局注册 Element Plus 图标，页面中可直接使用 <User />、<Calendar /> 等组件。
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
