/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Design System Colors (LedgerFlow)
        primary: "#155E58",
        "primary-deep": "#0D3B38",
        "primary-hover": "#0D3B38",
        "primary-soft": "#1E8278",
        aqua: "#3ABFB1",
        background: "#F7F5F0",
        surface: "#ffffff",
        "surface-alt": "#FBFAF6",
        border: "#D9E3DD",
        "border-light": "#EDF1EC",
        "text-primary": "#0D3B38",
        "text-secondary": "#6D837B",
        "text-muted": "#94A8A0",
        "highlight-bg": "#E7F5F1",
        "tab-bg": "#D5F1EA",
        
        // Backward compatibility
        ink: "#0D3B38",
        muted: "#6D837B",
        mist: "#F7F5F0",
        line: "#D9E3DD",
        brand: "#155E58",
        accent: "#1E8278",
        success: "#1E8278",
        warning: "#9A641A",
        danger: "#A33A32"
      },
      boxShadow: {
        panel: "0 18px 50px rgba(13, 59, 56, 0.08)",
        soft: "0 1px 2px rgba(13, 59, 56, 0.06)",
        lg: "0 14px 34px rgba(13, 59, 56, 0.12)"
      },
      animation: {
        "slide-in-left": "slideInFromLeft 0.6s ease-out",
        "slide-in-right": "slideInFromRight 0.6s ease-out",
        "slide-in-top": "slideInFromTop 0.6s ease-out",
        "slide-in-bottom": "slideInFromBottom 0.6s ease-out",
        "fade-in": "fadeIn 0.6s ease-out",
        "fade-in-scale": "fadeInScale 0.5s ease-out",
        "stagger-in": "staggerIn 0.4s ease-out",
        "float-soft": "floatSoft 5s ease-in-out infinite",
        "shine": "shine 2.8s ease-in-out infinite"
      },
      keyframes: {
        slideInFromLeft: {
          from: { opacity: "0", transform: "translateX(-40px)" },
          to: { opacity: "1", transform: "translateX(0)" }
        },
        slideInFromRight: {
          from: { opacity: "0", transform: "translateX(40px)" },
          to: { opacity: "1", transform: "translateX(0)" }
        },
        slideInFromTop: {
          from: { opacity: "0", transform: "translateY(-30px)" },
          to: { opacity: "1", transform: "translateY(0)" }
        },
        slideInFromBottom: {
          from: { opacity: "0", transform: "translateY(30px)" },
          to: { opacity: "1", transform: "translateY(0)" }
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" }
        },
        fadeInScale: {
          from: { opacity: "0", transform: "scale(0.95)" },
          to: { opacity: "1", transform: "scale(1)" }
        },
        staggerIn: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" }
        },
        floatSoft: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" }
        },
        shine: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" }
        }
      }
    }
  },
  plugins: []
};
