import { describe, expect, it, vi } from "vitest";
import { getConsumo, getEnvios, reintentarEnvio, enviarPrueba } from "../api";

describe("API de notificaciones", () => {
  it("consulta consumo con rango", async () => {
    const request = vi.fn().mockResolvedValue({ desde: "a", hasta: "b", items: [] });
    await getConsumo(request as any, "2026-01-01", "2026-01-31");
    expect(request).toHaveBeenCalledWith(
      "/notificaciones/consumo?desde=2026-01-01&hasta=2026-01-31",
    );
  });

  it("lista envíos con filtros", async () => {
    const request = vi.fn().mockResolvedValue([]);
    await getEnvios(request as any, "fallida", "turno-1");
    expect(request).toHaveBeenCalledWith(
      "/notificaciones/envios?estado=fallida&turno_id=turno-1",
    );
  });

  it("reintenta un envío", async () => {
    const request = vi.fn().mockResolvedValue({ id: "e1", estado: "encolada" });
    await reintentarEnvio(request as any, "e1");
    expect(request).toHaveBeenCalledWith(
      "/notificaciones/envios/e1/reintentar",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("envía prueba auditada", async () => {
    const request = vi.fn().mockResolvedValue({ id: "e2", estado: "encolada", canal: "whatsapp" });
    await enviarPrueba(request as any, { paciente_id: "p1", canal: "whatsapp" });
    expect(request).toHaveBeenCalledWith(
      "/notificaciones/test",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
