import { createRouter, createWebHistory } from 'vue-router'
import SetupView from '../views/SetupView.vue'
import GradingView from '../views/GradingView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/setup' },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/grading', name: 'grading', component: GradingView },
  ],
})
