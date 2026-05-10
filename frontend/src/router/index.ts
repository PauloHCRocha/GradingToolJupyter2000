import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'
import SetupView from '../views/SetupView.vue'
import GradingView from '../views/GradingView.vue'
import PlagiarismView from '../views/PlagiarismView.vue'

export const router = createRouter({
  // import.meta.env.BASE_URL picks up the value from vite.config (`/` in
  // dev, `/GradingToolJupyter2000/` in production) so the router resolves
  // routes relative to where the app is actually mounted.
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/grading', name: 'grading', component: GradingView },
    { path: '/plagiarism', name: 'plagiarism', component: PlagiarismView },
  ],
})
