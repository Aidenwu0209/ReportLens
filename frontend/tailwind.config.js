/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Finance blue (deep) + Electric blue (interaction)
        'primary': {
          DEFAULT: '#1a3a5c',
          light: '#2563eb',
          electric: '#3b82f6',
          hover: '#60a5fa',
        },
        // Near-black blue background
        'surface': {
          DEFAULT: '#0a0f1a',
          card: 'rgba(15, 23, 42, 0.75)',
          elevated: 'rgba(30, 41, 59, 0.85)',
        },
        // Status colors
        'status': {
          success: '#06b6d4',   // cyan
          info: '#f59e0b',      // amber
          risk: '#991b1b',      // dark red
          'risk-light': '#ef4444',
        },
        // Text
        'text': {
          primary: '#f1f5f9',
          secondary: '#94a3b8',
          muted: '#64748b',
        },
      },
      borderRadius: {
        'card': '12px',
      },
      backdropBlur: {
        'card': '16px',
      },
      boxShadow: {
        'card': '0 4px 24px rgba(0, 0, 0, 0.3)',
        'glow': '0 0 20px rgba(59, 130, 246, 0.15)',
      },
      animation: {
        'scan': 'scan 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        scan: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(100%)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
