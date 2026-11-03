import { apiClient } from "../../shared/api/client";
import type { ApiErrorAction, ApiErrorBody } from "../../shared/api/client";

export type { ApiErrorAction, ApiErrorBody };

export interface TurnoAgenda {
  id: string;
  paciente_id: string;
  profesional_id: string;
  profesional_usuario_id: string | null;
  prestacion_id: string | null;
  inicio: string;
  fin: string;
  estado: string;
  origen: string;
  sobreturno: boolean;
  sobreturno_motivo: string | null;
  sobreturno_autorizado_por: string | null;
  senia_id: string | null;
  cancelled_by: string | null;
  cancelled_at: string | null;
  motivo: string | null;
}

export interface TurnoInput {
  paciente_id: string;
  profesional_id: string;
  prestacion_id: string | null;
  inicio: string;
  fin: string;
  sobreturno: boolean;
  sobreturno_motivo: string | null;
}

export interface ReprogramarTurnoInput {
  profesional_id: string;
  prestacion_id: string | null;
  inicio: string;
  fin: string;
}

export interface ReprogramarTurnoResultado {
  turno_anterior: TurnoAgenda;
  turno_nuevo: TurnoAgenda;
}

export type AgendaRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

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

export function consultarAgenda(
  request: AgendaRequest,
  vista: "dia" | "semana",
  fecha: string,
  profesionalId?: string,
): Promise<TurnoAgenda[]> {
  const query = new URLSearchParams({ fecha });
  if (profesionalId) query.set("profesional_id", profesionalId);
  return request<TurnoAgenda[]>(`/agenda/${vista}?${query.toString()}`);
}

export function consultarDisponibilidad(
  request: AgendaRequest,
  profesionalId: string,
  prestacionId: string,
  desde: string,
  hasta: string,
): Promise<string[]> {
  const query = new URLSearchParams({
    profesional_id: profesionalId,
    prestacion_id: prestacionId,
    desde,
    hasta,
  });
  return request<string[]>(`/agenda/disponibilidad?${query.toString()}`);
}

export function crearTurno(
  request: AgendaRequest,
  input: TurnoInput,
  idempotencyKey: string,
): Promise<TurnoAgenda> {
  return request<TurnoAgenda>("/turnos", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(input),
  });
}

export function ejecutarAccionTurno(
  request: AgendaRequest,
  turnoId: string,
  accion: "confirmar" | "presente" | "ausente",
): Promise<TurnoAgenda> {
  return request<TurnoAgenda>(
    `/turnos/${encodeURIComponent(turnoId)}/${accion}`,
    { method: "POST" },
  );
}

export function reprogramarTurno(
  request: AgendaRequest,
  turnoId: string,
  input: ReprogramarTurnoInput,
): Promise<ReprogramarTurnoResultado> {
  return request<ReprogramarTurnoResultado>(
    `/turnos/${encodeURIComponent(turnoId)}/reprogramar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
}
