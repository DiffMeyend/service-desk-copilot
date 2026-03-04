/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // High-contrast neon green theme
        neon: {
          50: '#f0fff4',
          100: '#d0ffe0',
          200: '#a0ffc0',
          300: '#70ff9f',
          400: '#39ff14',  // Main neon green
          500: '#32e00c',
          600: '#28b809',
          700: '#208f07',
          800: '#186605',
          900: '#103d03',
        },
        primary: {
          50: '#f0fff4',
          100: '#d0ffe0',
          200: '#a0ffc0',
          300: '#70ff9f',
          400: '#39ff14',  // Neon green
          500: '#39ff14',
          600: '#32e00c',
          700: '#28b809',
          800: '#208f07',
          900: '#186605',
        },
        // CSS score colors - using neon green for high
        css: {
          low: '#ff3131',      // Neon red
          medium: '#ffff00',   // Neon yellow
          high: '#39ff14',     // Neon green
        },
      },
    },
  },
  plugins: [],
}
