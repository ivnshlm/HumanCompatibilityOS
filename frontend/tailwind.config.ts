import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Calm risk palette by doctrine — high is muted orange, never red.
        // Source of truth for class-based risk colour stays in lib/risk.ts.
        risk: {
          low: "#34d399", // emerald-400
          medium: "#fbbf24", // amber-400
          high: "#fb923c", // orange-400
        },
      },
    },
  },
  plugins: [],
};

export default config;
