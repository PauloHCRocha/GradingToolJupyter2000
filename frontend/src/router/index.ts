import { createRouter, createWebHistory } from 'vue-router'
import SetupView from '../views/SetupView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/setup' },
    { path: '/setup', name: 'setup', component: SetupView },
  ],
})
