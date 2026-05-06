import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// `base` matters for the GitHub Pages build (the site lives under
// `/GradingToolJupyter2000/`). Local dev (`npm run dev`) keeps the root.
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: command === 'build' ? '/GradingToolJupyter2000/' : '/',
  build: {
    chunkSizeWarningLimit: 1500,
  },
}))
