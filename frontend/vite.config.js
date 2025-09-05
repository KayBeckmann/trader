import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Build server config dynamically to avoid misconfigurations that cause reload loops
  const server = {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://api-server:8000',
        changeOrigin: true,
      },
      // Important: target should be the server root; Vite appends the path
      '/ws/predictions': {
        target: 'ws://api-server:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  }

  // Only set allowedHosts if provided; leaving it undefined allows local/dev hosts
  if (env.VITE_ALLOWED_HOST) {
    server.allowedHosts = [env.VITE_ALLOWED_HOST]
  }

  // Only configure custom HMR if explicitly provided via env to avoid bad defaults
  if (env.VITE_HMR_HOST) {
    server.hmr = {
      host: env.VITE_HMR_HOST,
      protocol: env.VITE_HMR_PROTOCOL || 'ws',
      port: env.VITE_HMR_PORT ? Number(env.VITE_HMR_PORT) : undefined,
    }
  }

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server,
  }
})
