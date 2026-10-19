import { apiClient } from "../../shared/api/client";
import type { ApiErrorAction, ApiErrorBody } from "../../shared/api/client";

export type { ApiErrorAction, ApiErrorBody };

/** Alias histórico: el slice de agenda nombra así a la acción de reprogramar. */
export type ReprogramarAction = ApiErrorAction;

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
  return apiClient.request<TurnoCancelado>(
    `/turnos/${encodeURIComponent(turnoId)}/cancelar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ motivo }),
    },
  );
}
