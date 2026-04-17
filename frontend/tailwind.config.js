/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: {
          50: '#fbfaf8',   // Background
          100: '#f4f1ea',  // Secondary BG / Panels
          200: '#e8e4d8',  // Borders
          300: '#d1cdc0',  // Muted text
          700: '#5d5d5d',  // Secondary text / Stone
          800: '#2c2c2c',  // Primary text / Ink
          900: '#1a1a1a',  // Deepest text
        },
        accent: {
          50: '#fdfcfb',
          100: '#f7f4f0',
          500: '#8c7e6a',  // Warm taupe
          600: '#706555',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['"Libre Baskerville"', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};
