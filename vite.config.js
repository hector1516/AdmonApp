import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// SPA plano (sin SvelteKit): index.html -> src/main.js -> App.svelte
export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      $lib: '/src/lib'
    }
  },
  server: {
    host: true,
    port: 5173
  },
  build: {
    outDir: 'dist'
  }
});
