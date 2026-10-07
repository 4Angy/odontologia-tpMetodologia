import { useState } from "react";
import type { FormEvent } from "react";
import { cancelarTurnoApi } from "./api";
import type { ApiErrorBody, CancelarTurnoFn, TurnoCancelado } from "./api";

export type { CancelarTurnoFn };

interface CancelarTurnoModalProps {
  turnoId: string;
  abierto: boolean;
  onCerrar: () => void;
  onCancelado?: (turno: TurnoCancelado) => void;
  cancelarTurno?: CancelarTurnoFn;
}

function esApiError(err: unknown): err is ApiErrorBody {
  if (typeof err !== "object" || err === null) return false;
  const e = err as Record<string, unknown>;
  return typeof e["code"] === "string" && typeof e["message"] === "string";
}

export function CancelarTurnoModal({
  turnoId,
  abierto,
  onCerrar,
  onCancelado,
  cancelarTurno = cancelarTurnoApi,
}: CancelarTurnoModalProps): JSX.Element | null {
  const [motivo, setMotivo] = useState<string>("");
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [enviando, setEnviando] = useState<boolean>(false);

  if (!abierto) return null;

  const motivoValido: boolean = motivo.trim().length > 0;

  async function onSubmit(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (!motivoValido || enviando) return;
    setEnviando(true);
    setError(null);
    try {
      const turno = await cancelarTurno(turnoId, motivo.trim());
      onCancelado?.(turno);
      onCerrar();
    } catch (err: unknown) {
      setError(esApiError(err) ? err : { code: "DESCONOCIDO", message: "Error inesperado." });
    } finally {
      setEnviando(false);
    }
  }

  const esFueraDeTermino: boolean = error?.code === "RN-AG-01";

  return (
    <div role="dialog" aria-modal="true" aria-label="Cancelar turno">
      <h2>Cancelar turno</h2>
      <form onSubmit={onSubmit}>
        <label htmlFor="motivo-cancelacion">Motivo</label>
        <textarea
          id="motivo-cancelacion"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={500}
        />
        <button type="submit" disabled={!motivoValido || enviando}>
          Confirmar cancelación
        </button>
        <button type="button" onClick={onCerrar}>
          Volver
        </button>
      </form>
      {error !== null && (
        <div role="alert">
          <p>{error.message}</p>
          {esFueraDeTermino && error.action !== undefined && (
            <div>
              {/* Placeholder C-07: reprogramar aún no existe como capability. */}
              <button type="button" disabled title={error.action.hint}>
                Reprogramar
              </button>
              <p>{error.action.hint}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface CancelarTurnoButtonProps {
  turnoId: string;
  onCancelado?: (turno: TurnoCancelado) => void;
  cancelarTurno?: CancelarTurnoFn;
}

export function CancelarTurnoButton({
  turnoId,
  onCancelado,
  cancelarTurno,
}: CancelarTurnoButtonProps): JSX.Element {
  const [abierto, setAbierto] = useState<boolean>(false);
  return (
    <>
      <button type="button" onClick={() => setAbierto(true)}>
        Cancelar turno
      </button>
      <CancelarTurnoModal
        turnoId={turnoId}
        abierto={abierto}
        onCerrar={() => setAbierto(false)}
        onCancelado={onCancelado}
        cancelarTurno={cancelarTurno}
      />
    </>
  );
}
