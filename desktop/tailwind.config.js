/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand': '#b63d1f',
        'brand-2': '#0f6d7a',
        'bg': '#f3efe6',
        'bg-2': '#e7e0d3',
        'panel': '#fff8e8',
        'text': '#1f1a16',
        'muted': '#6d5d4f',
        'line': '#d8c7b4',
        'ok': '#2c7a47',
        'warn': '#b05a05',
        'danger': '#a11d2f',
      },
      borderRadius: {
        'DEFAULT': '16px',
      },
      fontFamily: {
        'sans': ['"Noto Sans SC"', 'sans-serif'],
        'brand': ['"ZCOOL QingKe HuangYou"', 'cursive'],
      },
    },
  },
  plugins: [],
}
