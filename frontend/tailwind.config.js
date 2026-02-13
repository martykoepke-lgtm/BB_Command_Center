/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brand palette — dark mode default
        brand: {
          50: "#e6f1ff",
          100: "#b3d7ff",
          200: "#80bdff",
          300: "#4da3ff",
          400: "#1a89ff",
          500: "#0070f3",
          600: "#005ac2",
          700: "#004391",
          800: "#002d61",
          900: "#001630",
        },
        // Status colors (consistent across all views per CLAUDE.md)
        status: {
          success: "#22c55e",   // green — on track / complete
          warning: "#eab308",   // yellow — at risk
          danger: "#ef4444",    // red — blocked / overdue
          active: "#3b82f6",    // blue — accent / active
          tag: "#a855f7",       // purple — type tags
          ai: "#14b8a6",        // teal — AI interactions
        },
        // Dark theme surface colors
        surface: {
          bg: "#0f172a",        // slate-900
          card: "#1e293b",      // slate-800
          hover: "#334155",     // slate-700
          border: "#475569",    // slate-600
          muted: "#64748b",     // slate-500
        },
      },
    },
  },
  plugins: [],
};
