import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import type { ProxyOptions } from "vite";

const API = "http://localhost:8000";

// La SPA y la API comparten prefijos de ruta (`/agenda`, `/pacientes`, `/r/...`).
// La navegación del navegador (Accept: text/html) debe servir `index.html`;
// los fetch de datos del SPA (Accept: */* o application/json) van al backend.
function conBypassSpa(): ProxyOptions {
  return {
    target: API,
    bypass(req) {
      if (req.headers.accept?.includes("text/html")) return "/index.html";
    },
  };
}

const API_PREFIXES = [
  "/auth",
  "/me",
  "/users",
  "/agenda",
  "/pacientes",
  "/notificaciones",
  "/public",
  "/r",
  "/webhooks",
  "/cobros",
  "/deudas",
  "/caja",
  "/turnos",
  "/profesionales",
  "/prestaciones",
  "/bloqueos",
  "/config",
  "/senias",
] as const;

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(API_PREFIXES.map((p) => [p, conBypassSpa()])),
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test-setup.ts"],
  },
});
