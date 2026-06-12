import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pink:  { DEFAULT: "#FE9EC7", light: "#FFD0E6", dark: "#FC6FA8" },
        cream: { DEFAULT: "#F9F6C4", light: "#FDFBE8", dark: "#F0EB8A" },
        sky:   { DEFAULT: "#89D4FF", light: "#C4EAFF", dark: "#5BBFFF" },
        blue:  { DEFAULT: "#44ACFF", light: "#7DC8FF", dark: "#1A8FE8" },
        riq: {
          pink:  "#FE9EC7",
          cream: "#F9F6C4",
          sky:   "#89D4FF",
          blue:  "#44ACFF",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        "riq-gradient": "linear-gradient(135deg, #FE9EC7 0%, #89D4FF 50%, #44ACFF 100%)",
        "riq-soft":     "linear-gradient(135deg, #FFF5F9 0%, #F0F9FF 100%)",
        "card-shine":   "linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.4) 100%)",
      },
      animation: {
        "fade-in":       "fadeIn 0.4s ease forwards",
        "slide-up":      "slideUp 0.5s ease forwards",
        "pulse-slow":    "pulse 3s ease-in-out infinite",
        "shimmer":       "shimmer 2s linear infinite",
        "float":         "float 6s ease-in-out infinite",
        "spin-slow":     "spin 8s linear infinite",
        "bounce-gentle": "bounceGentle 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:        { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp:       { from: { opacity: "0", transform: "translateY(20px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        shimmer:       { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        float:         { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-12px)" } },
        bounceGentle:  { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
      },
      boxShadow: {
        "riq-sm": "0 2px 8px rgba(68,172,255,0.15), 0 1px 3px rgba(0,0,0,0.06)",
        "riq-md": "0 4px 20px rgba(68,172,255,0.2), 0 2px 8px rgba(0,0,0,0.08)",
        "riq-lg": "0 8px 40px rgba(254,158,199,0.25), 0 4px 16px rgba(68,172,255,0.15)",
        "riq-xl": "0 20px 60px rgba(254,158,199,0.3), 0 8px 24px rgba(68,172,255,0.2)",
        "pink":   "0 4px 20px rgba(254,158,199,0.4)",
        "blue":   "0 4px 20px rgba(68,172,255,0.4)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
} satisfies Config;
