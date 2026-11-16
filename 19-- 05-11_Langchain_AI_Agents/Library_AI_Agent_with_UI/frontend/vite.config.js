import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The React app runs on http://localhost:5173 and the Python server on port 8000.
// The proxy forwards every /api/... request to Python, so the browser sees one
// address and no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
