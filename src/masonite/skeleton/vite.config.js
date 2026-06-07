/* Vite builds the application assets. By default we compile the CSS file
for the application (with Tailwind CSS) as well as bundling up the JS files.
The output lands in storage/compiled, which Masonite serves under /static. */
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [tailwindcss()],
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
