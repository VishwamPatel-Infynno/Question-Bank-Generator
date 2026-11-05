import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const gracefulShutdownPlugin = () => ({
  name: 'graceful-shutdown',
  configureServer(server) {
    const handleExit = () => {
      server.close().then(() => {
        process.exit(0);
      }).catch(() => {
        process.exit(0);
      });
    };
    process.once('SIGINT', handleExit);
    process.once('SIGTERM', handleExit);
  }
})

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
// Extra dev-server hosts (e.g. a tunnel hostname) come from VITE_ALLOWED_HOSTS in the repo-root
// .env, comma-separated, instead of a hostname committed to the repo.
const env = loadEnv(mode, path.resolve(process.cwd(), '..'), 'VITE_')
const allowedHosts = (env.VITE_ALLOWED_HOSTS || '').split(',').map((h) => h.trim()).filter(Boolean)

return {
  plugins: [react(), gracefulShutdownPlugin()],
  server: {
    port: 5173,
    allowedHosts,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            if (err.code === 'ECONNREFUSED') {
              if (res.writeHead && !res.headersSent) {
                res.writeHead(503, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Backend server is starting up...', status: 'starting' }));
              }
              return;
            }
            console.error('[vite-proxy-error]', err);
          });
        }
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/lucide-react')) {
            return 'vendor-icons';
          }
          // Exact package paths: a bare 'node_modules/react' prefix also matches react-* packages
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) {
            return 'vendor-react';
          }
        }
      }
    }
  }
}
})
