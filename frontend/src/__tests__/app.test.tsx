import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRutas } from "../App";
import { AppShell } from "../shared/ui/AppShell";
import { AuthProvider, type AuthUser } from "../features/auth/auth";

const usuarioDemo: AuthUser = {
  sub: "u-demo",
  email: "demo@demo.com",
  nombre: "Demo",
  roles: ["recepcion", "odontologo", "dueno"],
  permisos: [],
};

function renderEn(ruta: string): void {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <AuthProvider initialUser={usuarioDemo}>
        <AppShell>
          <AppRutas />
        </AppShell>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Shell de la aplicación", () => {
  it("monta el shell con los enlaces principales", () => {
    renderEn("/agenda");

    expect(screen.getByRole("heading", { name: /consultorio odontológico/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /agenda/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pacientes/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /caja/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /configuración/i })).toBeInTheDocument();
  });

  it("resuelve la ruta /agenda a su página", () => {
    renderEn("/agenda");

    expect(screen.getByRole("heading", { name: /^agenda$/i })).toBeInTheDocument();
  });

  it("resuelve la ruta /caja a su página", () => {
    renderEn("/caja");

    expect(screen.getByRole("heading", { name: /^caja$/i })).toBeInTheDocument();
  });

  it("muestra la página de no encontrada para una ruta desconocida", () => {
    renderEn("/ruta-inexistente");

    expect(screen.getByRole("heading", { name: /página no encontrada/i })).toBeInTheDocument();
  });
});
