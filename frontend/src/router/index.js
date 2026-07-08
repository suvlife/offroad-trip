import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/planning',
    name: 'planning',
    component: () => import('@/views/PlanningView.vue'),
  },
  {
    path: '/route/:id',
    name: 'route-detail',
    component: () => import('@/views/RouteView.vue'),
    props: true,
  },
  {
    path: '/share/:shareId',
    name: 'share',
    component: () => import('@/views/ShareView.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
