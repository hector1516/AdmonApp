/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{html,js,svelte,ts}',
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0F172A',
        surface: '#1E293B',
        primary: '#FF6B00',
        secondary: '#FFAE00',
        text: '#F8FAFC',
        muted: '#64748B',
        accent: '#FFB400',
      }
    }
  },
  plugins: []
}