import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";

export function LoginPage(): JSX.Element {
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    clearError();
    setEnviando(true);
    try {
      await login(email, password);
      navigate("/agenda", { replace: true });
    } catch {
      // El contexto traduce el error al mensaje de la interfaz.
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main>
      <h1>Ingresar al consultorio</h1>
      <form onSubmit={enviar}>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error !== null && <p role="alert">{error}</p>}
        <button type="submit" disabled={enviando}>
          {enviando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
      <Link to="/reset-password">¿Olvidaste tu contraseña?</Link>
    </main>
  );
}
