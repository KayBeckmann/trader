import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: '0.0.0.0',
      allowedHosts: [
        env.VITE_ALLOWED_HOST
      ],
      hmr: {
        protocol: 'wss',
        host: 'projekt.beckmann-md.de',
        port: 443
      },
      proxy: {
        '/api': {
          target: 'http://api-server:8000',
          changeOrigin: true,
        },
        '/ws/predictions': {
          target: 'ws://api-server:8000/ws/predictions',
          ws: true,
          changeOrigin: true,
        }
      }
    }
  }
})
