import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter-tight)", "system-ui", "sans-serif"],
      },
      colors: {
        // Design-system surface/text/accent tokens (P1).
        surface: "#121826",
        "surface-2": "#0f1422",
        edge: "#212a3b",
        "edge-2": "#1a2232",
        ink: "#e8edf5",
        "ink-muted": "#9aa3b8",
        "ink-faint": "#5f6982",
        accent: "#6d72e0",
        // Calm risk palette by doctrine — high is muted orange, never red.
        // Source of truth for class-based risk colour stays in lib/risk.ts.
        risk: {
          low: "#34d399", // emerald-400
          medium: "#fbbf24", // amber-400
          high: "#fb923c", // orange-400
        },
      },
      borderRadius: {
        card: "1rem", // 16px cards
        control: "0.625rem", // 10px controls
      },
    },
  },
  plugins: [],
};

export default config;
