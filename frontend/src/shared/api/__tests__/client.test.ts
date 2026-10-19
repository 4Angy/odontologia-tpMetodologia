import { describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError, GENERIC_ERROR_CODE, GENERIC_ERROR_MESSAGE } from "../client";

function respuestaJson(cuerpo: unknown, status: number): Response {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient", () => {
  it("traduce el sobre de error del backend a un ApiError con code, message y action", async () => {
    const fetchImpl = vi.fn(async () =>
      respuestaJson(
        {
          code: "RN-AG-01",
          message: "No se puede cancelar con menos de 24 h de antelación.",
          action: { type: "reprogramar", hint: "Coordiná manualmente un nuevo horario." },
        },
        409,
      ),
    );
    const cliente = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    const error = await cliente
      .request("/turnos/t-1/cancelar")
      .then(() => null)
      .catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.code).toBe("RN-AG-01");
    expect(apiError.message).toBe("No se puede cancelar con menos de 24 h de antelación.");
    expect(apiError.action?.type).toBe("reprogramar");
    expect(apiError.action?.hint).toBe("Coordiná manualmente un nuevo horario.");
    expect(apiError.status).toBe(409);
  });

  it("usa el código genérico cuando la respuesta de error no trae code", async () => {
    const fetchImpl = vi.fn(async () => respuestaJson({ detalle: "algo raro" }, 500));
    const cliente = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    const error = (await cliente.request("/salud").catch((e: unknown) => e)) as ApiError;

    expect(error.code).toBe(GENERIC_ERROR_CODE);
    expect(error.message).toBe(GENERIC_ERROR_MESSAGE);
    expect(error.status).toBe(500);
  });

  it("devuelve el cuerpo parseado cuando la respuesta es exitosa", async () => {
    const fetchImpl = vi.fn(async () => respuestaJson({ id: "turno-1", estado: "cancelado" }, 200));
    const cliente = new ApiClient({ fetchImpl: fetchImpl as unknown as typeof fetch });

    const resultado = await cliente.request<{ id: string; estado: string }>("/turnos/turno-1");

    expect(resultado).toEqual({ id: "turno-1", estado: "cancelado" });
  });

  it("arma la url con la base configurada", async () => {
    const fetchImpl = vi.fn(async () => respuestaJson({}, 200));
    const cliente = new ApiClient({
      baseUrl: "http://api.ejemplo.com/",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    await cliente.request("/agenda/dia");

    expect(cliente.url("/agenda/dia")).toBe("http://api.ejemplo.com/agenda/dia");
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://api.ejemplo.com/agenda/dia",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
