import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiClient, type ApiClient } from "../../shared/api/client";

interface ResetPasswordPageProps {
  client?: ApiClient;
}

export function ResetPasswordPage({ client = apiClient }: ResetPasswordPageProps): JSX.Element {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [nuevaPassword, setNuevaPassword] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function solicitar(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const respuesta = await client.request<{ message: string; token?: string }>("/auth/password-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setMensaje(respuesta.message);
      if (respuesta.token !== undefined) setToken(respuesta.token);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo solicitar el reset.");
    }
  }

  async function confirmar(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const respuesta = await client.request<{ message: string }>("/auth/password-reset/confirmar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, nueva_password: nuevaPassword }),
      });
      setMensaje(respuesta.message);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "El token no es válido o ya fue utilizado.",
      );
    }
  }

  return (
    <main>
      <h1>Restablecer contraseña</h1>
      <form onSubmit={solicitar}>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <button type="submit">Solicitar token</button>
      </form>
      <form onSubmit={confirmar}>
        <label>
          Token
          <input value={token} onChange={(event) => setToken(event.target.value)} required />
        </label>
        <label>
          Nueva contraseña
          <input
            type="password"
            value={nuevaPassword}
            onChange={(event) => setNuevaPassword(event.target.value)}
            required
          />
        </label>
        <button type="submit">Cambiar contraseña</button>
      </form>
      {mensaje !== null && <p role="status">{mensaje}</p>}
      {error !== null && <p role="alert">{error}</p>}
      <Link to="/login">Volver a ingresar</Link>
    </main>
  );
}
