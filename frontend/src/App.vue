<template>
  <div class="min-h-screen bg-background text-text font-sans antialiased">
    <!-- 登录页 -->
    <div v-if="isLogin">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>

    <!-- 主应用台 -->
    <div v-else class="flex min-h-screen">
      <!-- 侧边栏 -->
      <aside class="w-64 flex-shrink-0 flex flex-col bg-surface/80 backdrop-blur-xl border-r border-border fixed h-full z-30 transition-all duration-300">
        <!-- Logo区 -->
        <div class="h-20 flex items-center px-6 border-b border-border/50">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-2xl bg-accent/10 flex items-center justify-center border border-accent/20 shadow-[0_0_15px_rgba(var(--accent),0.2)]">
              <span class="text-xl animate-pulse">🛡️</span>
            </div>
            <div>
              <h1 class="text-base font-bold tracking-tight">AliCDT Manager</h1>
              <p class="text-xs text-text-muted font-medium">流量守护</p>
            </div>
          </div>
        </div>

        <!-- 导航菜单 -->
        <nav class="flex-1 px-4 py-6 relative">
          <!-- 滑动指示器：改为使用 transform 实现 GPU 加速，计算更精准 -->
          <div
            class="absolute left-4 right-4 h-11 rounded-xl bg-accent/10 border border-accent/20 transition-transform duration-300 cubic-bezier(0.4, 0, 0.2, 1) pointer-events-none"
            :style="{ transform: `translateY(${activeIndex * 52}px)` }"
          ></div>

          <!-- 导航项列表 -->
          <div class="flex flex-col gap-2 relative z-10">
            <div
              v-for="(item, index) in navItems"
              :key="item.path"
              class="flex items-center gap-3 px-4 h-11 rounded-xl text-sm font-medium cursor-pointer transition-colors duration-200"
              :class="activeIndex === index ? 'text-accent' : 'text-text-muted hover:text-text hover:bg-surface-hover/50'"
              @click="navigate(item.path)"
            >
              <span class="text-lg opacity-80 transition-opacity" :class="{ 'opacity-100': activeIndex === index }">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </nav>

        <!-- 底部操作 -->
        <div class="p-4 border-t border-border/50">
          <button @click="logout"
            class="w-full flex items-center justify-center gap-2 px-4 h-11 rounded-xl text-sm font-medium text-text-muted hover:text-danger hover:bg-danger/10 transition-colors duration-200 group">
            <span class="group-hover:-translate-x-1 transition-transform duration-200">🚪</span>
            <span>退出登录</span>
          </button>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="ml-64 flex-1 min-h-screen bg-background relative overflow-x-hidden">
        <div class="p-8 max-w-7xl mx-auto">
          <!-- 路由过渡动画 -->
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
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

// 智能计算激活状态：废弃容易脱节的 watch，改用纯 computed
// 增加了对子路由（如 /accounts/detail）的高亮支持
const activeIndex = computed(() => {
  const index = navItems.findIndex(item => {
    if (item.path === '/') return route.path === '/'
    return route.path.startsWith(item.path)
  })
  return index === -1 ? 0 : index
})

function navigate(path) {
  router.push(path)
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
/* 路由切换：缩放与透明度融合的现代过渡效果 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(15px) scale(0.99);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-15px) scale(0.99);
}

/* 基础渐变效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
