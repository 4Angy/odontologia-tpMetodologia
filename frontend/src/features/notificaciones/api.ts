import type { AgendaRequest } from "../agenda/api";

export interface ConsumoItem {
  canal: string;
  estado: string;
  cantidad: number;
  costo_centavos: number;
}

export interface ConsumoResponse {
  desde: string;
  hasta: string;
  items: ConsumoItem[];
}

export interface NotificacionEnvio {
  id: string;
  tenant_id: string;
  paciente_id: string;
  turno_id: string | null;
  canal: string;
  plantilla_codigo: string;
  ventana: string | null;
  estado: string;
  motivo_code: string | null;
  intentos: number;
  next_attempt_at: string;
  provider_msg_id: string | null;
  costo_estimado_centavos: number;
  ultimo_error_code: string | null;
  enviado_at: string | null;
  entregado_at: string | null;
}

export async function getConsumo(
  request: AgendaRequest,
  desde: string,
  hasta: string,
): Promise<ConsumoResponse> {
  return request<ConsumoResponse>(
    `/notificaciones/consumo?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}`,
  );
}

export async function getEnvios(
  request: AgendaRequest,
  estado?: string,
  turnoId?: string,
): Promise<NotificacionEnvio[]> {
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (turnoId) params.set("turno_id", turnoId);
  const qs = params.toString();
  return request<NotificacionEnvio[]>(
    `/notificaciones/envios${qs ? `?${qs}` : ""}`,
  );
}

export async function reintentarEnvio(
  request: AgendaRequest,
  id: string,
): Promise<{ id: string; estado: string }> {
  return request<{ id: string; estado: string }>(
    `/notificaciones/envios/${encodeURIComponent(id)}/reintentar`,
    { method: "POST" },
  );
}

export async function enviarPrueba(
  request: AgendaRequest,
  payload: { paciente_id: string; canal?: string },
): Promise<{ id: string; estado: string; canal: string }> {
  return request<{ id: string; estado: string; canal: string }>(
    "/notificaciones/test",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) },
  );
}
