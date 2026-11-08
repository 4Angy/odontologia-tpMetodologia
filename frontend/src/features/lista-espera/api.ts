import type { AgendaRequest } from "../agenda/api";

export interface ListaEsperaItem {
  id: string;
  tenant_id: string;
  paciente_id: string;
  profesional_id: string | null;
  prestacion_id: string | null;
  prioridad: number;
  estado: string;
  motivo_omision: string | null;
  hueco_profesional_id: string | null;
  hueco_inicio: string | null;
  hueco_fin: string | null;
  hueco_prestacion_id: string | null;
  ofrecido_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export async function getListaEspera(request: AgendaRequest, estado?: string): Promise<ListaEsperaItem[]> {
  const qs = estado ? `?estado=${encodeURIComponent(estado)}` : "";
  return request<ListaEsperaItem[]>(`/lista-espera${qs}`);
}

export async function crearListaEspera(
  request: AgendaRequest,
  payload: { paciente_id: string; profesional_id?: string | null; prestacion_id?: string | null; prioridad?: number },
): Promise<ListaEsperaItem> {
  return request<ListaEsperaItem>("/lista-espera", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
