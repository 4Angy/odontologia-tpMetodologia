import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../../../shared/api/client";
import {
  cancelPublicBooking,
  confirmPublicBooking,
  createPublicBooking,
  getPublicAvailability,
  reschedulePublicBooking,
} from "../api";

vi.mock("../../../shared/api/client", () => ({
  apiClient: { request: vi.fn() },
}));

describe("API de reserva pública", () => {
  it("consulta disponibilidad con filtros y fechas UTC", async () => {
    vi.mocked(apiClient.request).mockResolvedValue({});

    await getPublicAvailability(
      "demo consultorio",
      "prof-1",
      "service-1",
      "2030-01-01T12:00:00.000Z",
      "2030-01-02T12:00:00.000Z",
    );

    expect(apiClient.request).toHaveBeenCalledWith(
      "/r/demo%20consultorio?desde=2030-01-01T12%3A00%3A00.000Z&hasta=2030-01-02T12%3A00%3A00.000Z&profesional_id=prof-1&prestacion_id=service-1",
    );
  });

  it("usa rutas codificadas para confirmar y cancelar por token", async () => {
    vi.mocked(apiClient.request).mockResolvedValue({
      turno_id: "turno-1",
      estado: "confirmado",
    });

    await confirmPublicBooking("token/con slash", "demo");
    await cancelPublicBooking("token/con slash", "demo");
    expect(apiClient.request).toHaveBeenNthCalledWith(
      1,
      "/public/turnos/token%2Fcon%20slash/confirmar",
      expect.objectContaining({ method: "POST" }),
    );
    expect(apiClient.request).toHaveBeenNthCalledWith(
      2,
      "/public/turnos/token%2Fcon%20slash/cancelar",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("envía idempotencia y conserva checkout pendiente", async () => {
    const payload = {
      tenant_slug: "demo",
      profesional_id: "prof-1",
      prestacion_id: "service-1",
      inicio: "2030-01-02T15:00:00.000Z",
      nombre: "Ana",
      apellido: "Pérez",
      whatsapp_opt_in: false,
    };
    vi.mocked(apiClient.request).mockResolvedValue({
      turno_id: "turno-3",
      estado: "pendiente_confirmacion",
      action_tokens: {},
      checkout_url: "https://checkout.example/3",
    });

    await createPublicBooking(payload, "idempotency-1");

    expect(apiClient.request).toHaveBeenCalledWith(
      "/public/reservar",
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": "idempotency-1",
        },
        body: JSON.stringify(payload),
      }),
    );
  });

  it("serializa reprogramación con instante timezone-aware", async () => {
    const payload = {
      tenant_slug: "demo",
      profesional_id: "prof-1",
      prestacion_id: "service-1",
      inicio: "2030-01-02T15:00:00.000Z",
    };
    expect(payload.inicio.endsWith("Z")).toBe(true);
    vi.mocked(apiClient.request).mockResolvedValue({
      turno_id: "turno-2",
      estado: "pendiente_confirmacion",
      action_tokens: {},
      checkout_url: null,
    });
    await reschedulePublicBooking("token-1", payload);
    expect(apiClient.request).toHaveBeenCalledWith(
      "/public/turnos/token-1/reprogramar",
      expect.objectContaining({
        body: JSON.stringify(payload),
      }),
    );
  });
});
