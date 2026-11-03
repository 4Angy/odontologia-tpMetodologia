import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ApiClient } from "../../../shared/api/client";
import { AuthProvider, type AuthUser } from "../../auth/auth";
import { PacientesPage } from "../PacientesPage";

const recepcion: AuthUser = {
  sub: "recepcion-1",
  email: "recepcion@example.test",
  nombre: "Recepción",
  roles: ["recepcion"],
  permisos: ["pacientes"],
};

const odontologo: AuthUser = {
  sub: "odontologo-1",
  email: "odontologo@example.test",
  nombre: "Odontóloga",
  roles: ["odontologo"],
  permisos: ["pacientes", "evoluciones", "presupuestos"],
};

const paciente = {
  id: "p-1",
  tenant_id: "t-1",
  nombre: "Julia",
  apellido: "Sosa",
  dni: "30123456",
  telefono: "+5491122223333",
  email: "julia@example.test",
  fecha_nac: null,
  notas: null,
  saldo: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function respuesta(cuerpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status });
}

function renderPacientes(
  path: string,
  fetchImpl: typeof fetch,
  usuario: AuthUser = recepcion,
): void {
  const client = new ApiClient({ fetchImpl });
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider client={client} initialUser={usuario} restoreSession={false}>
        <Routes>
          <Route path="/pacientes" element={<PacientesPage />} />
          <Route path="/pacientes/:pacienteId" element={<PacientesPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("gestión de pacientes", () => {
  it("muestra lista, busca y abre un resultado", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta([paciente]))
      .mockResolvedValueOnce(respuesta([paciente]));
    renderPacientes("/pacientes", fetchImpl as unknown as typeof fetch);

    expect(await screen.findByRole("link", { name: /julia sosa/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/buscar/i), { target: { value: "30123456" } });
    fireEvent.submit(screen.getByRole("button", { name: /buscar/i }).closest("form")!);

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(2));
    expect(fetchImpl.mock.calls[1]?.[0]).toContain("q=30123456");
  });

  it("permite dar de alta un paciente y muestra validaciones del servidor", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(respuesta({ code: "RN-PA-01", message: "El teléfono no es válido." }, 422));
    renderPacientes("/pacientes", fetchImpl as unknown as typeof fetch);

    await screen.findByRole("heading", { name: /^pacientes$/i });
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Ana" } });
    fireEvent.change(screen.getByLabelText("Apellido"), { target: { value: "Paz" } });
    fireEvent.change(screen.getByLabelText(/^teléfono$/i), { target: { value: "123" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar paciente/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("El teléfono no es válido.");
  });

  it("expone estados de carga y lista vacía", async () => {
    let resolver: ((value: Response) => void) | undefined;
    const fetchImpl = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolver = resolve;
        }),
    );
    renderPacientes("/pacientes", fetchImpl as unknown as typeof fetch);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
    resolver?.(respuesta([]));
    expect(await screen.findByText(/no hay pacientes/i)).toBeInTheDocument();
  });

  it("presenta consentimiento, estado de opt-in y acción de revocación", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta(paciente))
      .mockResolvedValueOnce(respuesta([
        {
          id: "o-1",
          paciente_id: "p-1",
          tenant_id: "t-1",
          canal: "whatsapp",
          estado: true,
          updated_at: "2026-01-01T00:00:00Z",
          consentimiento_version: "wa-v1",
          consentimiento_actor_id: "recepcion-1",
          consentimiento_at: "2026-01-01T00:00:00Z",
        },
      ]))
      .mockResolvedValueOnce(respuesta([]));
    renderPacientes("/pacientes/p-1", fetchImpl as unknown as typeof fetch);

    expect(await screen.findByRole("heading", { name: /julia sosa/i })).toBeInTheDocument();
    expect(screen.getByText(/wa-v1/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /revocar/i })).toBeInTheDocument();
  });

  it("requiere confirmación y versión antes de activar el opt-in", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta(paciente))
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(
        respuesta([
          {
            id: "b-1",
            paciente_id: "p-1",
            tenant_id: "t-1",
            estado: "aprobado",
            total_cents: 15000,
            notas: null,
            items: [{ id: "i-1", descripcion: "Control", monto_cents: 15000 }],
            created_at: "2026-11-03T15:00:00Z",
            updated_at: "2026-11-03T15:00:00Z",
          },
        ]),
      )
      .mockResolvedValueOnce(
        respuesta({
          id: "o-1",
          paciente_id: "p-1",
          tenant_id: "t-1",
          canal: "whatsapp",
          estado: true,
          updated_at: "2026-01-01T00:00:00Z",
          consentimiento_version: "wa-v2",
          consentimiento_actor_id: "recepcion-1",
          consentimiento_at: "2026-01-01T00:00:00Z",
        }),
      );
    renderPacientes("/pacientes/p-1", fetchImpl as unknown as typeof fetch);

    await screen.findByRole("heading", { name: /julia sosa/i });
    fireEvent.click(screen.getByRole("button", { name: /activar whatsapp/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/consentimiento explícito/i);
    expect(fetchImpl).toHaveBeenCalledTimes(3);

    fireEvent.change(screen.getByLabelText(/versión del texto presentado/i), {
      target: { value: "wa-v2" },
    });
    fireEvent.click(screen.getByLabelText(/confirmo que el paciente dio su consentimiento/i));
    fireEvent.click(screen.getByRole("button", { name: /activar whatsapp/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/consentimiento registrado/i);
    expect(fetchImpl).toHaveBeenCalledTimes(4);
    const request = fetchImpl.mock.calls[3];
    expect(request?.[0]).toContain("/pacientes/p-1/optins");
    expect(request?.[1]).toEqual(
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          canal: "whatsapp",
          estado: true,
          version_texto: "wa-v2",
        }),
      }),
    );
  });

  it("edita el contacto y refresca las preferencias tras cambiar el teléfono", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta(paciente))
      .mockResolvedValueOnce(respuesta([
        {
          id: "o-1",
          paciente_id: "p-1",
          tenant_id: "t-1",
          canal: "whatsapp",
          estado: true,
          updated_at: "2026-01-01T00:00:00Z",
          consentimiento_version: "wa-v1",
          consentimiento_actor_id: "recepcion-1",
          consentimiento_at: "2026-01-01T00:00:00Z",
        },
      ]))
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(respuesta({ ...paciente, telefono: "+5491144445555" }))
      .mockResolvedValueOnce(respuesta([
        {
          id: "o-1",
          paciente_id: "p-1",
          tenant_id: "t-1",
          canal: "whatsapp",
          estado: false,
          updated_at: "2026-01-02T00:00:00Z",
          consentimiento_version: "wa-v1",
          consentimiento_actor_id: "recepcion-1",
          consentimiento_at: "2026-01-01T00:00:00Z",
        },
      ]));
    renderPacientes("/pacientes/p-1", fetchImpl as unknown as typeof fetch);

    await screen.findByRole("heading", { name: /julia sosa/i });
    fireEvent.change(screen.getByLabelText(/^teléfono$/i), {
      target: { value: "+5491144445555" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/opt-in.*revocado/i);
    expect(screen.getAllByText("Inactivo")).toHaveLength(2);
  });

  it("muestra el reporte por fila de la importación", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(
        respuesta({
          importadas: 1,
          duplicadas: 1,
          fallidas: 1,
          resultados: [
            { fila: 2, estado: "importada", paciente_id: "p-1" },
            { fila: 3, estado: "duplicada", code: "RN-PA-02", mensaje: "Duplicado." },
            { fila: 4, estado: "fallida", code: "RN-PA-01", mensaje: "Fila inválida." },
          ],
        }),
      )
      .mockResolvedValueOnce(respuesta([paciente]));
    renderPacientes("/pacientes", fetchImpl as unknown as typeof fetch);

    await screen.findByRole("heading", { name: /^pacientes$/i });
    const file = new File(["nombre,apellido\nAna,Paz"], "pacientes.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText(/archivo csv/i), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /importar/i }));

    expect(await screen.findByText(/importadas: 1/i)).toBeInTheDocument();
    expect(screen.getByText(/fila 4.*inválida/i)).toBeInTheDocument();
  });

  it("descarga el CSV exportado desde la API", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(new Response("nombre,apellido\nJulia,Sosa", { status: 200 }));
    const createObjectURL = vi.fn(() => "blob:pacientes");
    const revokeObjectURL = vi.fn();
    const clickedLinks: HTMLAnchorElement[] = [];
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        clickedLinks.push(this);
      });
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    renderPacientes("/pacientes", fetchImpl as unknown as typeof fetch);

    await screen.findByRole("heading", { name: /^pacientes$/i });
    fireEvent.click(screen.getByRole("button", { name: /exportar pacientes csv/i }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(2));
    expect(fetchImpl.mock.calls[1]?.[0]).toContain("/export/pacientes.csv");
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(clickedLinks[0]?.href).toBe("blob:pacientes");
    expect(clickedLinks[0]?.download).toBe("pacientes.csv");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:pacientes");
    clickSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("integra timeline clínico, adjuntos y presupuestos para odontología", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta(paciente))
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(
        respuesta([
          {
            id: "b-1",
            paciente_id: "p-1",
            tenant_id: "t-1",
            estado: "aprobado",
            total_cents: 15000,
            notas: null,
            items: [{ id: "i-1", descripcion: "Control", monto_cents: 15000 }],
            created_at: "2026-11-03T15:00:00Z",
            updated_at: "2026-11-03T15:00:00Z",
          },
        ]),
      )
      .mockResolvedValueOnce(
        respuesta([
          {
            id: "e-1",
            paciente_id: "p-1",
            tenant_id: "t-1",
            profesional_id: "prof-1",
            fecha: "2026-11-03T15:00:00Z",
            motivo: "Control sintético",
            detalle: "Detalle sintético",
            pieza_fdi_slot: "tooth",
            pieza_fdi_numero: 11,
            odontograma_ref: null,
            firma_simple: true,
            firmado_at: "2026-11-03T15:00:00Z",
            alcance_firma: "Firma simple; no constituye firma digital.",
            updated_at: "2026-11-03T15:00:00Z",
          },
        ]),
      )
      .mockResolvedValueOnce(
        respuesta([
          {
            id: "a-1",
            paciente_id: "p-1",
            tenant_id: "t-1",
            nombre: "radiografia.pdf",
            tipo: "application/pdf",
            tamano_bytes: 256,
            created_at: "2026-11-03T15:00:00Z",
            updated_at: "2026-11-03T15:00:00Z",
          },
        ]),
      );
    renderPacientes(
      "/pacientes/p-1",
      fetchImpl as unknown as typeof fetch,
      odontologo,
    );

    expect(await screen.findByText("Control sintético")).toBeInTheDocument();
    expect(screen.getByText("Detalle sintético")).toBeInTheDocument();
    expect(screen.getByText(/firma simple.*no constituye firma digital/i)).toBeInTheDocument();
    expect(screen.getByText("radiografia.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Presupuesto aprobado/i)).toBeInTheDocument();
    expect(screen.getAllByText(/15\.000/)).toHaveLength(2);
  });

  it("no solicita ni muestra evoluciones a recepción", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(respuesta(paciente))
      .mockResolvedValueOnce(respuesta([]))
      .mockResolvedValueOnce(respuesta([]));
    renderPacientes("/pacientes/p-1", fetchImpl as unknown as typeof fetch);

    expect(await screen.findByRole("heading", { name: /julia sosa/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /evoluciones clínicas/i })).not.toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(fetchImpl.mock.calls.some(([path]) => String(path).includes("/evoluciones"))).toBe(false);
    expect(fetchImpl.mock.calls.some(([path]) => String(path).includes("/adjuntos"))).toBe(false);
  });
});
