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
            <div class="text-sm font-semibold text-text">AliCDT Manager</div>
            <div class="text-[10px] text-text-muted">流量守护</div>
          </div>
        </div>
      </div>

      <!-- 导航 -->
      <nav class="flex-1 p-3 space-y-1 relative">
        <!-- 滑动指示器 -->
        <div
          class="absolute left-3 right-3 rounded-xl bg-accent/10 border border-accent/20 transition-all duration-200 ease-out pointer-events-none"
          :style="indicatorStyle"
        ></div>

        <div
          v-for="item in navItems"
          :key="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-colors duration-150 relative"
          :class="currentPath === item.path ? 'text-accent' : 'text-text-muted hover:text-text hover:bg-white/5'"
          @click="navigate(item.path)"
        >
          <span class="text-base">{{ item.icon }}</span>
          <span class="font-medium">{{ item.label }}</span>
        </div>
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
import { computed, ref, watch } from 'vue'
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

const currentPath = ref(route.path)

// 立即同步，不等路由完成
function navigate(path) {
  currentPath.value = path
  router.push(path)
}

// 保持同步（浏览器前进后退）
watch(() => route.path, (p) => {
  currentPath.value = p
})

// 计算滑动指示器位置
const indicatorStyle = computed(() => {
  const index = navItems.findIndex(item => item.path === currentPath.value)
  const i = index === -1 ? 0 : index
  // 每个item高度约44px，间距4px
  const top = i * 48 + 4
  return {
    top: `${top}px`,
    height: '40px',
  }
})

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>
