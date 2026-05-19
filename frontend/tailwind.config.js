/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "../app/templates/**/*.html",
    "./src/**/*.ts",
  ],
  theme: {
    extend: {
      colors: {
        primary: "var(--color-primary)",
        surface: "var(--color-surface)",
        "surface-alt": "var(--color-surface-alt)",
        positive: "var(--color-positive)",
        negative: "var(--color-negative)",
        warning: "var(--color-warning)",
      },
    },
  },
  plugins: [],
};
