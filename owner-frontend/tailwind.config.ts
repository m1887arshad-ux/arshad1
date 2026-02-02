import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2563eb",
        "primary-dark": "#1d4ed8",
        sidebar: "#1e3a5f",
        "sidebar-active": "#2c5282",
        pending: "#ea580c",
        approved: "#16a34a",
        rejected: "#dc2626",
      },
    },
  },
  plugins: [],
};

export default config;
