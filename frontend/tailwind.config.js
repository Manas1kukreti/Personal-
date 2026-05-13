/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#162033",
        muted: "#667085",
        mist: "#f6f8fb",
        line: "#d9e2ec",
        brand: "#0f766e",
        accent: "#2563eb",
        success: "#059669",
        warning: "#d97706",
        danger: "#dc2626"
      },
      boxShadow: {
        panel: "0 18px 45px rgba(16, 24, 40, 0.08)",
        soft: "0 1px 2px rgba(16, 24, 40, 0.05)"
      }
    }
  },
  plugins: []
};
