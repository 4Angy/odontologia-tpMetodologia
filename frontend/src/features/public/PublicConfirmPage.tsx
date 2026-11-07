import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { confirmPublicBooking } from "./api";
import { ApiError } from "../../shared/api/client";

type Estado = "cargando" | "exito" | "expirado" | "revocado" | "error";

export function PublicConfirmPage(): JSX.Element {
  const { slug = "" } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [estado, setEstado] = useState<Estado>("cargando");
  const [mensaje, setMensaje] = useState("Confirmando tu turno…");

  useEffect(() => {
    if (!token) {
      setEstado("error");
      setMensaje("Falta el enlace de confirmación.");
      return;
    }
    let activo = true;
    void confirmPublicBooking(token, slug)
      .then((result) => {
        if (!activo) return;
        setEstado("exito");
        setMensaje(`Turno ${result.estado}. Tu acuse quedó registrado.`);
      })
      .catch((error: unknown) => {
        if (!activo) return;
        if (error instanceof ApiError) {
          if (error.code === "RN-AU-03" || /venci/i.test(error.message)) {
            setEstado("expirado");
            setMensaje("El enlace venció o ya no es válido.");
            return;
          }
          if (/revoc/i.test(error.message)) {
            setEstado("revocado");
            setMensaje("El enlace fue revocado.");
            return;
          }
        }
        setEstado("error");
        setMensaje("No pudimos confirmar el turno. Probá de nuevo.");
      });
    return () => {
      activo = false;
    };
  }, [slug, token]);

  return (
    <main aria-labelledby="confirm-title">
      <h1 id="confirm-title">Confirmación de turno</h1>
      <p role="status">{mensaje}</p>
      {estado === "exito" && <p>Gracias por confirmar.</p>}
      {estado === "expirado" && <p>Pedí un nuevo enlace al consultorio.</p>}
      {estado === "revocado" && <p>El enlace fue revocado por el consultorio.</p>}
      {estado === "error" && <p>Verificá tu conexión e intentá de nuevo.</p>}
    </main>
  );
}
