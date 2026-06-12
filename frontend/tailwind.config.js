/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0B1220",
          card: "#111827",
          elevated: "#1a2332",
        },
        border: {
          DEFAULT: "#1F2937",
          light: "#374151",
        },
        accent: {
          DEFAULT: "#D4622A",
          dim: "#B8521F",
          light: "#E8955A",
          glow: "rgba(212, 98, 42, 0.18)",
        },
        warn: "#F59E0B",
        danger: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
    },
  },
  plugins: [],
};
