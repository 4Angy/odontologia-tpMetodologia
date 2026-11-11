import { apiClient } from "../../shared/api/client";

export interface PublicCatalogItem {
  id: string;
  nombre: string;
  duracion_min?: number;
  /** C-12: la reserva exige seña por Mercado Pago. */
  senia_requerida?: boolean;
  senia_monto_cents?: number | null;
}

export interface PublicAvailability {
  tenant_slug: string;
  tenant_name: string;
  professionals: PublicCatalogItem[];
  services: PublicCatalogItem[];
  slots: string[];
}

export interface PublicBooking {
  turno_id: string;
  estado: string;
  action_tokens: Record<string, string>;
  checkout_url: string | null;
}

export interface PublicActionResponse {
  turno_id: string;
  estado: string;
}

export interface PublicReschedulePayload {
  tenant_slug: string;
  profesional_id: string;
  prestacion_id: string;
  inicio: string;
}

export interface PublicBookingPayload {
  tenant_slug: string;
  profesional_id: string;
  prestacion_id: string;
  inicio: string;
  nombre: string;
  apellido: string;
  telefono?: string;
  email?: string;
  whatsapp_opt_in: boolean;
}

export function getPublicAvailability(
  slug: string,
  profesionalId: string | undefined,
  prestacionId: string | undefined,
  desde: string,
  hasta: string,
): Promise<PublicAvailability> {
  const query = new URLSearchParams({ desde, hasta });
  if (profesionalId) query.set("profesional_id", profesionalId);
  if (prestacionId) query.set("prestacion_id", prestacionId);
  return apiClient.request<PublicAvailability>(`/r/${encodeURIComponent(slug)}?${query}`);
}

export function createPublicBooking(
  payload: PublicBookingPayload,
  idempotencyKey: string,
): Promise<PublicBooking> {
  return apiClient.request<PublicBooking>("/public/reservar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(payload),
  });
}

export function confirmPublicBooking(
  token: string,
  tenantSlug: string,
): Promise<PublicActionResponse> {
  return publicAction(token, "confirmar", { tenant_slug: tenantSlug });
}

export function cancelPublicBooking(
  token: string,
  tenantSlug: string,
): Promise<PublicActionResponse> {
  return publicAction(token, "cancelar", { tenant_slug: tenantSlug });
}

export function reschedulePublicBooking(
  token: string,
  payload: PublicReschedulePayload,
): Promise<PublicBooking> {
  return apiClient.request<PublicBooking>(
    `/public/turnos/${encodeURIComponent(token)}/reprogramar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

function publicAction(
  token: string,
  action: "confirmar" | "cancelar",
  payload: { tenant_slug: string },
): Promise<PublicActionResponse> {
  return apiClient.request<PublicActionResponse>(
    `/public/turnos/${encodeURIComponent(token)}/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}
