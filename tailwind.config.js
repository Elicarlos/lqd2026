/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./participante/templates/**/*.html",
    "./lojista/templates/**/*.html",
    "./bcp/templates/**/*.html",
    "./cupom/templates/**/*.html",
    "./static/css/tailwind/**/*.css",
  ],
  safelist: [
    // Cores personalizadas que podem não ser detectadas
    {
      pattern: /bg-\[#[0-9a-fA-F]{6}\]/,
    },
    {
      pattern: /text-\[#[0-9a-fA-F]{6}\]/,
    },
    {
      pattern: /border-\[#[0-9a-fA-F]{6}\]/,
    },
    {
      pattern: /hover:bg-\[#[0-9a-fA-F]{6}\]/,
    },
    {
      pattern: /hover:text-\[#[0-9a-fA-F]{6}\]/,
    },
    // Classes de brand que podem ser geradas dinamicamente
    'bg-brand-primary',
    'bg-brand-primary-light', 
    'bg-brand-primary-dark',
    'bg-brand-secondary',
    'bg-brand-accent',
    'text-brand-primary',
    'text-brand-primary-light',
    'text-brand-primary-dark', 
    'text-brand-secondary',
    'text-brand-accent',
    'border-brand-primary',
    'border-brand-secondary',
    'hover:bg-brand-primary',
    'hover:bg-brand-primary-dark',
    'hover:text-brand-primary',
    'focus:ring-brand-primary',
    // Classes de status
    'bg-status-success',
    'bg-status-error', 
    'bg-status-warning',
    'bg-status-info',
    'text-status-success',
    'text-status-error',
    'text-status-warning', 
    'text-status-info',
    'border-status-success',
    'border-status-error',
    'border-status-warning',
    'border-status-info',
    // Animações e delays
    'animate-fade-in',
    'animate-slide-up',
    'animate-delay-100',
    'animate-delay-200',
    'animate-delay-300',
    // Classes dinâmicas comuns
    'col-span-1',
    'col-span-2',
    'col-span-3',
    'col-span-4',
    'col-span-8',
    'row-start-1',
    'row-start-2',
    'row-end-1',
    'row-end-2',
    'grid-cols-1',
    'grid-cols-2',
    'grid-cols-3',
    'grid-cols-4',
    'grid-cols-5',
    'grid-cols-6',
    'grid-cols-12',
    'md:grid-cols-2',
    'md:grid-cols-3',
    'md:grid-cols-4',
    'lg:grid-cols-2',
    'lg:grid-cols-3',
    'lg:grid-cols-4',
    'lg:grid-cols-5',
  ],
  presets: [
    {
      theme: {
        extend: {
          colors: {
            'brand': {
              primary: 'var(--brand-primary)',
              'primary-light': 'var(--brand-primary-light)',
              'primary-dark': 'var(--brand-primary-dark)',
              secondary: 'var(--brand-secondary)',
              accent: 'var(--brand-accent)',
            },
            'neutral': {
              50: 'var(--neutral-50)',
              100: 'var(--neutral-100)',
              200: 'var(--neutral-200)',
              300: 'var(--neutral-300)',
              400: 'var(--neutral-400)',
              500: 'var(--neutral-500)',
              600: 'var(--neutral-600)',
              700: 'var(--neutral-700)',
              800: 'var(--neutral-800)',
              900: 'var(--neutral-900)',
            },
            'status': {
              success: 'var(--success-500)',
              error: 'var(--error-500)',
              warning: 'var(--warning-500)',
              info: 'var(--info-500)',
            }
          },
          spacing: {
            'xs': 'var(--spacing-xs)',
            'sm': 'var(--spacing-sm)',
            'md': 'var(--spacing-md)',
            'lg': 'var(--spacing-lg)',
            'xl': 'var(--spacing-xl)',
          },
          borderRadius: {
            'sm': 'var(--radius-sm)',
            'md': 'var(--radius-md)',
            'lg': 'var(--radius-lg)',
            'xl': 'var(--radius-xl)',
          },
          fontFamily: {
            sans: ['var(--font-sans)'],
            display: ['var(--font-display)'],
          },
          boxShadow: {
            'sm': 'var(--shadow-sm)',
            'md': 'var(--shadow-md)',
            'lg': 'var(--shadow-lg)',
          },
          zIndex: {
            0: 'var(--z-0)',
            10: 'var(--z-10)',
            20: 'var(--z-20)',
            30: 'var(--z-30)',
            40: 'var(--z-40)',
            50: 'var(--z-50)',
          },
        }
      }
    }
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px",
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        'brand': {
          primary: 'var(--brand-primary)',
          'primary-light': 'var(--brand-primary-light)',
          'primary-dark': 'var(--brand-primary-dark)',
          secondary: 'var(--brand-secondary)',
          accent: 'var(--brand-accent)',
        },
        'neutral': {
          50: 'var(--neutral-50)',
          100: 'var(--neutral-100)',
          200: 'var(--neutral-200)',
          300: 'var(--neutral-300)',
          400: 'var(--neutral-400)',
          500: 'var(--neutral-500)',
          600: 'var(--neutral-600)',
          700: 'var(--neutral-700)',
          800: 'var(--neutral-800)',
          900: 'var(--neutral-900)',
        },
        'status': {
          success: 'var(--success-500)',
          error: 'var(--error-500)',
          warning: 'var(--warning-500)',
          info: 'var(--info-500)',
        }
      },
      spacing: {
        'xs': 'var(--spacing-xs)',
        'sm': 'var(--spacing-sm)',
        'md': 'var(--spacing-md)',
        'lg': 'var(--spacing-lg)',
        'xl': 'var(--spacing-xl)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        display: ['var(--font-display)'],
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
      },
      zIndex: {
        0: 'var(--z-0)',
        10: 'var(--z-10)',
        20: 'var(--z-20)',
        30: 'var(--z-30)',
        40: 'var(--z-40)',
        50: 'var(--z-50)',
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "fade-in": {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        "fade-out": {
          from: { opacity: 1 },
          to: { opacity: 0 },
        },
        "slide-in": {
          from: { transform: "translateY(100%)" },
          to: { transform: "translateY(0)" },
        },
        "slide-out": {
          from: { transform: "translateY(0)" },
          to: { transform: "translateY(100%)" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        }
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.2s ease-out",
        "fade-out": "fade-out 0.2s ease-out",
        "slide-in": "slide-in 0.2s ease-out",
        "slide-out": "slide-out 0.2s ease-out",
        "float": "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms")({
      strategy: "class",
    }),
    require("tailwindcss-animate"),
  ],
}
