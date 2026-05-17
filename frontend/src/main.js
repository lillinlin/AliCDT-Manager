import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import Dashboard from './views/Dashboard.vue'
import Login from './views/Login.vue'
import Accounts from './views/Accounts.vue'
import Logs from './views/Logs.vue'
import Settings from './views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: Dashboard, meta: { auth: true } },
    { path: '/accounts', component: Accounts, meta: { auth: true } },
    { path: '/logs', component: Logs, meta: { auth: true } },
    { path: '/settings', component: Settings, meta: { auth: true } },
  ]
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.auth && !token) return next('/login')
  if (to.path === '/login' && token) return next('/')
  next()
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
