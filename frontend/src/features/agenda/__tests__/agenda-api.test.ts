import { describe, expect, it, vi } from "vitest";
import {
  consultarAgenda,
  consultarDisponibilidad,
  crearTurno,
  ejecutarAccionTurno,
  reprogramarTurno,
} from "../api";

describe("API de agenda interna", () => {
  it("consulta día o semana con filtros de período y profesional", async () => {
    const request = vi.fn().mockResolvedValue([]);

    await consultarAgenda(request, "semana", "2026-10-09", "prof 1");

    expect(request).toHaveBeenCalledWith(
      "/agenda/semana?fecha=2026-10-09&profesional_id=prof+1",
    );
  });

  it("consulta disponibilidad enviando instantes timezone-aware", async () => {
    const request = vi.fn().mockResolvedValue([]);

    await consultarDisponibilidad(
      request,
      "prof-1",
      "prest-1",
      "2026-10-09T03:00:00.000Z",
      "2026-10-10T03:00:00.000Z",
    );

    expect(request.mock.calls[0]?.[0]).toContain("/agenda/disponibilidad?");
    expect(request.mock.calls[0]?.[0]).toContain(
      "desde=2026-10-09T03%3A00%3A00.000Z",
    );
    expect(request.mock.calls[0]?.[0]).toContain("hasta=2026-10-10T03%3A00%3A00.000Z");
  });

  it("crea el turno con clave de idempotencia", async () => {
    const request = vi.fn().mockResolvedValue({});
    const input = {
      paciente_id: "pac-1",
      profesional_id: "prof-1",
      prestacion_id: null,
      inicio: "2026-10-09T12:00:00.000Z",
      fin: "2026-10-09T12:30:00.000Z",
      sobreturno: false,
      sobreturno_motivo: null,
    };

    await crearTurno(request, input, "key-1");

    expect(request).toHaveBeenCalledWith("/turnos", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": "key-1",
      },
      body: JSON.stringify(input),
    });
  });

  it("usa rutas de acciones explícitas y reprogramación", async () => {
    const request = vi.fn().mockResolvedValue({});

    await ejecutarAccionTurno(request, "turno/1", "presente");
    await reprogramarTurno(request, "turno/1", {
      profesional_id: "prof-1",
      prestacion_id: null,
      inicio: "2026-10-10T12:00:00.000Z",
      fin: "2026-10-10T12:30:00.000Z",
    });

    expect(request.mock.calls[0]?.[0]).toBe("/turnos/turno%2F1/presente");
    expect(request.mock.calls[1]?.[0]).toBe("/turnos/turno%2F1/reprogramar");
  });
});
