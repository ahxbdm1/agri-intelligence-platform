import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        midnight: "#07111f",
        panel: "rgba(12, 27, 45, 0.72)",
        cyanGlow: "#24d6c7",
        agriGreen: "#20d587",
        signalBlue: "#4fa3ff",
        warning: "#ffca55",
        danger: "#ff6b6b"
      },
      boxShadow: {
        glow: "0 0 36px rgba(36, 214, 199, 0.18)",
        card: "0 18px 70px rgba(0, 0, 0, 0.28)"
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px)",
        aurora: "radial-gradient(circle at 15% 15%, rgba(32,213,135,.18), transparent 36%), radial-gradient(circle at 88% 8%, rgba(79,163,255,.16), transparent 34%)"
      }
    }
  },
  plugins: []
};

export default config;
