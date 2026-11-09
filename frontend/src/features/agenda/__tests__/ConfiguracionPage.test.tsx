import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiClient } from "../../../shared/api/client";
import { AuthProvider, type AuthUser } from "../../auth/auth";
import { ConfiguracionPage } from "../ConfiguracionPage";

function respuesta(cuerpo: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(cuerpo), { status });
}

function usuario(rol: string): AuthUser {
  return {
    sub: `${rol}-demo`,
    email: `${rol}@example.test`,
    nombre: rol,
    roles: [rol],
    permisos: [],
  };
}

function renderConfiguracion(rol: string, fetchImpl: typeof fetch): void {
  render(
    <AuthProvider
      client={new ApiClient({ fetchImpl })}
      initialUser={usuario(rol)}
      restoreSession={false}
    >
      <ConfiguracionPage />
    </AuthProvider>,
  );
}

function respuestaCatalogos(
  fetchImpl: typeof fetch,
  profesionalesIniciales: Array<Record<string, unknown>> = [],
): typeof fetch {
  let profesional: Record<string, unknown> | null = profesionalesIniciales[0] ?? null;
  let prestacion: Record<string, unknown> | null = null;
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input);
    if (
      (url.endsWith("/profesionales") && init?.method === "POST") ||
      (url.includes("/profesionales/") && init?.method === "PUT")
    ) {
      const datos = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
      profesional = {
        id: "prof-1",
        tenant_id: "tenant-1",
        nombre: datos["nombre"] ?? "Dra. Demo",
        usuario_id: datos["usuario_id"] ?? null,
        color_agenda: datos["color_agenda"] ?? null,
        activo: datos["activo"] ?? true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      };
      return respuesta(profesional, init?.method === "POST" ? 201 : 200);
    }
    if (url.endsWith("/profesionales/prof-1") && init?.method === "DELETE") {
      profesional = null;
      return respuesta(null, 204);
    }
    if (
      (url.endsWith("/prestaciones") && init?.method === "POST") ||
      (url.includes("/prestaciones/") && init?.method === "PUT")
    ) {
      const datos = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
      prestacion = {
        id: "prest-1",
        tenant_id: "tenant-1",
        nombre: datos["nombre"] ?? "Limpieza",
        duracion_min: datos["duracion_min"] ?? 30,
        precio_ref: datos["precio_ref"] ?? null,
        activa: datos["activa"] ?? true,
        senia_requerida: datos["senia_requerida"] ?? null,
        senia_monto_cents: datos["senia_monto_cents"] ?? null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      };
      return respuesta(prestacion, init?.method === "POST" ? 201 : 200);
    }
    if (url.endsWith("/prestaciones/prest-1") && init?.method === "DELETE") {
      prestacion = null;
      return respuesta(null, 204);
    }
    if (url.endsWith("/profesionales")) {
      return respuesta(profesional === null ? [] : [profesional]);
    }
    if (url.endsWith("/horarios")) {
      return respuesta({ profesional_id: "prof-1", zona_horaria: "UTC", horarios: [] });
    }
    if (url.endsWith("/prestaciones")) return respuesta(prestacion === null ? [] : [prestacion]);
    if (url.endsWith("/bloqueos")) return respuesta([]);
    if (url.endsWith("/config")) {
      const datos = init?.method === "PUT"
        ? (JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>)
        : {};
      return respuesta({
        antelacion_cancel_hs: datos["antelacion_cancel_hs"] ?? 24,
        antelacion_reserva_hs: datos["antelacion_reserva_hs"] ?? 2,
        recordatorio_t_48h: datos["recordatorio_t_48h"] ?? true,
        recordatorio_t_24h: datos["recordatorio_t_24h"] ?? true,
        politica_devolucion_senia: datos["politica_devolucion_senia"] ?? "devuelve_100",
      });
    }
    return fetchImpl(input, init);
  });
}

describe("catálogo y configuración de agenda", () => {
  it("permite a recepción crear profesionales", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("recepcion", fetchImpl);

    expect(await screen.findByRole("heading", { name: /profesionales/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/nombre del profesional/i), {
      target: { value: "Dra. Demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar profesional/i }));

    expect(await screen.findAllByText("Dra. Demo")).not.toHaveLength(0);
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/profesionales"),
      expect.objectContaining({ method: "POST" }),
    ));
  });

  it("permite editar y eliminar un profesional de su catálogo", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch, [{
      id: "prof-1",
      tenant_id: "tenant-1",
      nombre: "Dra. Demo",
      usuario_id: null,
      color_agenda: null,
      activo: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }]);
    renderConfiguracion("recepcion", fetchImpl);

    await screen.findAllByText("Dra. Demo");
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText(/nombre del profesional/i), {
      target: { value: "Dra. Actualizada" },
    });
    fireEvent.click(screen.getByRole("button", { name: /actualizar profesional/i }));
    expect(await screen.findByText("Profesional actualizado.")).toBeInTheDocument();

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/profesionales/prof-1"),
      expect.objectContaining({ method: "PUT" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("Profesional eliminado.")).toBeInTheDocument();
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/profesionales/prof-1"),
      expect.objectContaining({ method: "DELETE" }),
    ));
  });

  it("permite crear, editar y eliminar prestaciones con importes en centavos", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("recepcion", fetchImpl);

    await screen.findByRole("heading", { name: /prestaciones/i });
    fireEvent.change(screen.getByLabelText(/nombre de la prestación/i), {
      target: { value: "Limpieza" },
    });
    fireEvent.change(screen.getByLabelText(/duración \(minutos\)/i), {
      target: { value: "30" },
    });
    fireEvent.change(screen.getByLabelText(/precio de referencia/i), {
      target: { value: "15000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar prestación/i }));
    expect(await screen.findByText("Prestación creada.")).toBeInTheDocument();

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/prestaciones"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          nombre: "Limpieza",
          duracion_min: 30,
          precio_ref: 15000,
          activa: true,
          senia_requerida: null,
          senia_monto_cents: null,
        }),
      }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText(/nombre de la prestación/i), {
      target: { value: "Limpieza actualizada" },
    });
    fireEvent.click(screen.getByRole("button", { name: /actualizar prestación/i }));
    expect(await screen.findByText("Prestación actualizada.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("Prestación eliminada.")).toBeInTheDocument();
  });

  it("permite consultar el catálogo sin exponer controles de escritura a odontología", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("odontologo", fetchImpl);

    expect(await screen.findByRole("heading", { name: /prestaciones/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /guardar profesional/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /guardar prestación/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/antelación mínima para reservar/i)).not.toBeInTheDocument();
  });

  it("muestra y permite guardar la configuración global solo al dueño", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("dueno", fetchImpl);

    expect(await screen.findByLabelText(/antelación mínima para cancelar/i)).toHaveValue(24);
    expect(screen.getByLabelText(/antelación mínima para reservar/i)).toHaveValue(2);
    fireEvent.change(screen.getByLabelText(/antelación mínima para reservar/i), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar configuración/i }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/config"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          antelacion_cancel_hs: 24,
          antelacion_reserva_hs: 3,
          recordatorio_t_48h: true,
          recordatorio_t_24h: true,
          politica_devolucion_senia: "devuelve_100",
        }),
      }),
    ));
  });

  it("guarda la seña por prestación con override y monto en centavos", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("recepcion", fetchImpl);

    await screen.findByRole("heading", { name: /prestaciones/i });
    fireEvent.change(screen.getByLabelText(/nombre de la prestación/i), {
      target: { value: "Endodoncia" },
    });
    fireEvent.change(screen.getByLabelText(/duración \(minutos\)/i), {
      target: { value: "45" },
    });
    fireEvent.change(screen.getByLabelText(/monto de la seña/i), {
      target: { value: "5000" },
    });
    fireEvent.change(screen.getByLabelText(/seña del turno/i), {
      target: { value: "si" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar prestación/i }));
    expect(await screen.findByText("Prestación creada.")).toBeInTheDocument();

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/prestaciones"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          nombre: "Endodoncia",
          duracion_min: 45,
          precio_ref: null,
          activa: true,
          senia_requerida: true,
          senia_monto_cents: 5000,
        }),
      }),
    ));
    expect(await screen.findByText(/seña 5000 centavos \(requerida\)/i)).toBeInTheDocument();
  });

  it("descarta el monto de seña cuando la prestación no requiere seña", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("recepcion", fetchImpl);

    await screen.findByRole("heading", { name: /prestaciones/i });
    fireEvent.change(screen.getByLabelText(/nombre de la prestación/i), {
      target: { value: "Consulta" },
    });
    fireEvent.change(screen.getByLabelText(/duración \(minutos\)/i), {
      target: { value: "30" },
    });
    fireEvent.change(screen.getByLabelText(/monto de la seña/i), {
      target: { value: "5000" },
    });
    fireEvent.change(screen.getByLabelText(/seña del turno/i), {
      target: { value: "no" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar prestación/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/no requiere seña/i);
    expect(fetchImpl).not.toHaveBeenCalledWith(
      expect.stringContaining("/prestaciones"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("permite al dueño elegir la política de devolución de seña", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch);
    renderConfiguracion("dueno", fetchImpl);

    expect(await screen.findByLabelText(/política de devolución de seña/i)).toHaveValue("devuelve_100");
    fireEvent.change(screen.getByLabelText(/política de devolución de seña/i), {
      target: { value: "devuelve_50" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar configuración/i }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      expect.stringContaining("/config"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          antelacion_cancel_hs: 24,
          antelacion_reserva_hs: 2,
          recordatorio_t_48h: true,
          recordatorio_t_24h: true,
          politica_devolucion_senia: "devuelve_50",
        }),
      }),
    ));
  });

  it("rechaza un bloqueo sin zona horaria y no envía la mutación", async () => {
    const fetchImpl = respuestaCatalogos(vi.fn() as unknown as typeof fetch, [{
      id: "prof-1",
      tenant_id: "tenant-1",
      nombre: "Dra. Demo",
      usuario_id: null,
      color_agenda: null,
      activo: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }]);
    renderConfiguracion("recepcion", fetchImpl);

    await screen.findByRole("heading", { name: /bloqueos/i });
    fireEvent.change(screen.getByLabelText(/profesional del bloqueo/i), {
      target: { value: "prof-1" },
    });
    fireEvent.change(screen.getByLabelText(/inicio \(iso 8601/i), {
      target: { value: "2026-11-02T10:00:00" },
    });
    fireEvent.change(screen.getByLabelText(/fin \(iso 8601/i), {
      target: { value: "2026-11-02T11:00:00-03:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /crear bloqueo/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/con zona horaria/i);
    expect(fetchImpl).not.toHaveBeenCalledWith(
      expect.stringContaining("/bloqueos"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("muestra los errores de autorización que devuelve la API", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
      if (String(input).endsWith("/profesionales")) {
        return respuesta({ code: "RN-AU-04", message: "Acceso denegado." }, 403);
      }
      if (String(input).endsWith("/prestaciones")) return respuesta([]);
      if (String(input).endsWith("/bloqueos")) return respuesta([]);
      return respuesta({
        antelacion_cancel_hs: 24,
        antelacion_reserva_hs: 2,
        recordatorio_t_48h: true,
        recordatorio_t_24h: true,
      });
    });
    renderConfiguracion("recepcion", fetchImpl as unknown as typeof fetch);

    expect(await screen.findByRole("alert")).toHaveTextContent("Acceso denegado.");
  });

  it("expone carga y estado vacío del catálogo", async () => {
    let resolver: ((value: Response) => void) | undefined;
    const fetchImpl = vi.fn((input: RequestInfo | URL): Promise<Response> => {
      if (String(input).endsWith("/profesionales")) {
        return new Promise((resolve) => {
          resolver = resolve;
        });
      }
      if (String(input).endsWith("/prestaciones")) return Promise.resolve(respuesta([]));
      if (String(input).endsWith("/bloqueos")) return Promise.resolve(respuesta([]));
      return Promise.resolve(respuesta({
        antelacion_cancel_hs: 24,
        antelacion_reserva_hs: 2,
        recordatorio_t_48h: true,
        recordatorio_t_24h: true,
      }));
    });
    renderConfiguracion("recepcion", fetchImpl as unknown as typeof fetch);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
    resolver?.(respuesta([]));
    expect(await screen.findByText("No hay profesionales cargados.")).toBeInTheDocument();
  });
});
