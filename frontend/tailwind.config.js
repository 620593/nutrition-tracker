/** @type {import('tailwindcss').Config} */
/*
 * This file configures Tailwind CSS for the Nutrition Tracker frontend.
 * It specifies which files Tailwind should scan to purge unused styles in production.
 * When fully implemented, it will also define a custom design system including the
 * brand color palette, extended typography scale, and any custom utility plugins
 * needed to support the glassmorphism and dark-mode aesthetic of the application.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
