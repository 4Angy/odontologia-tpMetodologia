import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://localhost:8000",
      "/me": "http://localhost:8000",
      "/users": "http://localhost:8000",
      "/agenda": "http://localhost:8000",
      "/pacientes": "http://localhost:8000",
      "/notificaciones": "http://localhost:8000",
      "/public": "http://localhost:8000",
      "/r": "http://localhost:8000",
      "/webhooks": "http://localhost:8000",
      "/cobros": "http://localhost:8000",
      "/deudas": "http://localhost:8000",
      "/caja": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test-setup.ts"],
  },
});
