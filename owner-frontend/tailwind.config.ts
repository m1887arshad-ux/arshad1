import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#2563eb",
        "primary-dark": "#1d4ed8",
        "primary-light": "#60a5fa",
        sidebar: "#1e3a5f",
        "sidebar-active": "#2c5282",
        "sidebar-dark": "#0f172a",
        "sidebar-active-dark": "#1e293b",
        pending: "#ea580c",
        approved: "#16a34a",
        rejected: "#dc2626",
      },
    },
  },
  plugins: [],
};

export default config;
