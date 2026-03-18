/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: "#6366f1",
        "accent-hover": "#4f46e5",
        "nav-start": "#1e1b4b",
        "nav-end": "#312e81",
      },
    },
  },
  plugins: [],
};
