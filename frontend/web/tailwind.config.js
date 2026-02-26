/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f1f7ff",
          500: "#2f6bff",
          700: "#234bd6"
        }
      }
    }
  },
  plugins: []
};
