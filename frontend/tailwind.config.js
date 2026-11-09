export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        epia: {
          900: "#0B2545",
          800: "#0F315E",
          700: "#13408A",
          500: "#1E6FF2",
          300: "#6FA8FF",
          100: "#E6F0FF",
          50: "#F4F8FF",
          surface: "#F8FAFC",
          cyan: "#06B6D4",
          ok: "#16A34A",
          warn: "#F59E0B",
          bad: "#DC2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
