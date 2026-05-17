<template>
  <div v-if="isLogin" class="min-h-screen">
    <router-view />
  </div>

  <div v-else class="flex min-h-screen">
    <!-- 侧边栏 -->
    <aside class="w-56 flex-shrink-0 flex flex-col glass border-r border-border fixed h-full z-20">
      <!-- Logo -->
      <div class="px-5 py-5 border-b border-border">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-accent flex items-center justify-center text-sm glow-pulse">🛡️</div>
          <div>
            <div class="text-sm font-semibold text-text">Aliyun Guard</div>
            <div class="text-[10px] text-text-muted">流量守护</div>
          </div>
        </div>
      </div>

      <!-- 导航 -->
      <nav class="flex-1 p-3 space-y-1">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 group"
          :class="$route.path === item.path
            ? 'bg-accent/10 text-accent border border-accent/20'
            : 'text-text-muted hover:text-text hover:bg-white/5'">
          <span class="text-base">{{ item.icon }}</span>
          <span class="font-medium">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 底部 -->
      <div class="p-3 border-t border-border">
        <button @click="logout"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-text-muted hover:text-danger hover:bg-danger/5 transition-all duration-200">
          <span>🚪</span><span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="ml-56 flex-1 min-h-screen">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isLogin = computed(() => route.path === '/login')

const navItems = [
  { path: '/', icon: '⚡', label: '总览' },
  { path: '/accounts', icon: '🔑', label: '账户管理' },
  { path: '/logs', icon: '📋', label: '系统日志' },
  { path: '/settings', icon: '⚙️', label: '系统设置' },
]

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>
