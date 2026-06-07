import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [tailwindcss(), vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./resources/js', import.meta.url)),
    },
  },
  build: {
    outDir: 'storage/compiled',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: 'resources/js/app.js',
      },
      output: {
        entryFileNames: 'js/[name].js',
        assetFileNames: (assetInfo) =>
          assetInfo.names?.some((name) => name.endsWith('.css'))
            ? 'css/[name][extname]'
            : 'assets/[name][extname]',
      },
    },
  },
})
