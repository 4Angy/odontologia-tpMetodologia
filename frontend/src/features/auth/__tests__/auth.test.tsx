import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, type AuthUser, useAuth } from "../auth";
import { AppRutas } from "../../../App";
import { AppShell } from "../../../shared/ui/AppShell";
import { ApiClient } from "../../../shared/api/client";

const usuario: AuthUser = {
  sub: "u-1",
  email: "u@demo.com",
  nombre: "Usuario",
  roles: ["odontologo"],
  permisos: [],
};

function respuesta(cuerpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status });
}

function AccionProtegida(): JSX.Element {
  const { request } = useAuth();
  return <button onClick={() => void request("/datos")}>Cargar</button>;
}

describe("AuthContext", () => {
  it("refresca una vez y reintenta la petición cuando el access expira", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta({ code: "RN-AU-01", message: "expirado" }, 401))
      .mockResolvedValueOnce(respuesta({ access_token: "nuevo", token_type: "bearer", expires_in: 900 }))
      .mockResolvedValueOnce(respuesta({ ...usuario, permisos: [] }))
      .mockResolvedValueOnce(respuesta({ ok: true }));
    const client = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    render(
      <AuthProvider client={client} initialUser={usuario} initialAccessToken="viejo">
        <AccionProtegida />
      </AuthProvider>,
    );

    screen.getByRole("button", { name: "Cargar" }).click();
    await screen.findByRole("button", { name: "Cargar" });
    expect(fetchImpl).toHaveBeenCalledTimes(4);
    const options = fetchImpl.mock.calls[3]?.[1] as RequestInit;
    expect((options.headers as Headers).get("Authorization")).toBe("Bearer nuevo");
  });
});

describe("guard de roles", () => {
  it("bloquea caja a un usuario que solo tiene recepción", () => {
    render(
      <MemoryRouter initialEntries={["/caja"]}>
        <AuthProvider initialUser={usuario}>
          <AppShell>
            <AppRutas />
          </AppShell>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Sin permiso" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Caja" })).not.toBeInTheDocument();
  });
});
