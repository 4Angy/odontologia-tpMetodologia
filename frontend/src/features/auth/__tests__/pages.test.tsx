import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../LoginPage";
import { ResetPasswordPage } from "../ResetPasswordPage";
import { AuthProvider, type AuthUser } from "../auth";
import { ApiClient } from "../../../shared/api/client";

const usuario: AuthUser = {
  sub: "u-1",
  email: "u@demo.com",
  nombre: "Usuario",
  roles: ["dueno"],
  permisos: [],
};

function respuesta(cuerpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status });
}

describe("pantallas de autenticación", () => {
  it("login exitoso carga identidad y navega al agenda", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta({ access_token: "access", token_type: "bearer", expires_in: 900 }))
      .mockResolvedValueOnce(respuesta(usuario));
    const client = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider client={client} restoreSession={false}>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@demo.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "secreto" } });
    fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("login inválido muestra el mensaje genérico del backend", async () => {
    const fetchImpl = vi.fn().mockResolvedValueOnce(
      respuesta({ code: "RN-AU-01", message: "Credenciales inválidas o ausentes." }, 401),
    );
    const client = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider client={client} initialUser={null} restoreSession={false}>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@demo.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "incorrecta" } });
    fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email o contraseña incorrectos.");
  });

  it("reset solicita token y confirma una nueva contraseña", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta({ message: "Si el email existe, recibirás instrucciones.", token: "token-demo" }))
      .mockResolvedValueOnce(respuesta({ message: "Contraseña actualizada." }));
    const client = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    render(
      <MemoryRouter>
        <ResetPasswordPage client={client} />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@demo.com" } });
    fireEvent.submit(screen.getByRole("button", { name: "Solicitar token" }));
    expect(await screen.findByDisplayValue("token-demo")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "nueva-segura" } });
    fireEvent.submit(screen.getByRole("button", { name: "Cambiar contraseña" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Contraseña actualizada.");
  });

  it("reset muestra error cuando el token es inválido", async () => {
    const fetchImpl = vi.fn().mockResolvedValueOnce(
      respuesta({ code: "RN-AU-02", message: "El token no es válido." }, 400),
    );
    const client = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    render(
      <MemoryRouter>
        <ResetPasswordPage client={client} />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Token"), { target: { value: "token-invalido" } });
    fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "nueva-segura" } });
    fireEvent.submit(screen.getByRole("button", { name: "Cambiar contraseña" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El token no es válido.");
  });
});
