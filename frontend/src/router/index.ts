import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'
import SetupView from '../views/SetupView.vue'
import GradingView from '../views/GradingView.vue'
import PlagiarismView from '../views/PlagiarismView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/grading', name: 'grading', component: GradingView },
    { path: '/plagiarism', name: 'plagiarism', component: PlagiarismView },
  ],
})
