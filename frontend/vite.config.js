import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api calls to the Flask backend so no CORS setup is needed in dev.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:5000" } },
});
