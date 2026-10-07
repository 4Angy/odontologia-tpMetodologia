export interface ReprogramarAction {
  type: "reprogramar";
  hint: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  action?: ReprogramarAction;
}

export interface TurnoCancelado {
  id: string;
  estado: string;
  cancelled_by: string | null;
  cancelled_at: string | null;
  motivo: string | null;
  senia_pendiente_definicion: boolean;
}

export type CancelarTurnoFn = (turnoId: string, motivo: string) => Promise<TurnoCancelado>;

export async function cancelarTurnoApi(turnoId: string, motivo: string): Promise<TurnoCancelado> {
  const res = await fetch(`/turnos/${encodeURIComponent(turnoId)}/cancelar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivo }),
  });
  const body: unknown = await res.json();
  if (!res.ok) {
    throw body as ApiErrorBody;
  }
  return body as TurnoCancelado;
}
