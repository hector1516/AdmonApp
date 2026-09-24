/** @type {import('vite').UserConfig} */
import svelte from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@sveltejs/plugin-tailwindcss';
import { defineConfig } from 'vite';
import svelteCheck from 'svelte-check';

export default defineConfig({
  plugins: [
    svelte(),
    tailwindcss(),
    // PWA plugin - configura manifest y service worker
    // @ts-ignore
    // vitePwa({
    //   registerType: 'autoUpdate',
    // })
  ],
  // Permitir importaciones absolutas $lib/
  resolve: {
    alias: {
      $lib: '/src/lib',
      $routes: '/src/routes',
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@use "svelte/types/javascript";'
      }
    }
  }
}