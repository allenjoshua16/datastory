/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#0f0f11',
          800: '#18181c',
          700: '#22222a',
          600: '#2a2a35',
        },
        gold: {
          DEFAULT: '#c9a96e',
          light: '#e0c898',
          dark: '#9a7a48',
        },
        muted: '#6b6964',
      },
      fontFamily: {
        serif: ['Georgia', 'serif'],
        mono: ['"Courier New"', 'monospace'],
      },
    },
  },
  plugins: [],
}
