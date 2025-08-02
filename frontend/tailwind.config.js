/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          bg: 'rgb(18, 18, 18)',
          card: 'rgb(29, 29, 29)',
          accent: 'rgb(168, 85, 247)',
          text: 'rgb(243, 244, 246)',
          'text-secondary': 'rgb(156, 163, 175)',
          border: 'rgb(55, 65, 81)',
        },
        chart: {
          teal: 'rgb(45, 212, 191)',
          pink: 'rgb(244, 114, 182)',
          yellow: 'rgb(251, 191, 36)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'default': '8px',
      },
      spacing: {
        '18': '4.5rem',
      }
    },
  },
  plugins: [],
}