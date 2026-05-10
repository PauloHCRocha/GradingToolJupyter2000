import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Hosted from the root on Cloudflare Pages (or any other static host).
export default defineConfig({
  plugins: [vue()],
  base: '/',
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
