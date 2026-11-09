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
      // La SPA reserva pública y la API comparten ruta (`/r/{slug}`): la
      // navegación del navegador (Accept: text/html) debe servir `index.html`,
      // mientras que los fetch de datos del SPA van al backend.
      "/r": {
        target: "http://localhost:8000",
        bypass(req) {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
      "/webhooks": "http://localhost:8000",
      "/cobros": "http://localhost:8000",
      "/deudas": "http://localhost:8000",
      "/caja": "http://localhost:8000",
      "/turnos": "http://localhost:8000",
      "/profesionales": "http://localhost:8000",
      "/prestaciones": "http://localhost:8000",
      "/bloqueos": "http://localhost:8000",
      "/config": "http://localhost:8000",
      "/senias": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test-setup.ts"],
  },
});
