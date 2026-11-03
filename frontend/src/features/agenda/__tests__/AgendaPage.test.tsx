import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "../../../shared/api/client";
import { AgendaPage } from "../AgendaPage";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  consultarAgenda: vi.fn(),
  consultarDisponibilidad: vi.fn(),
  crearTurno: vi.fn(),
  ejecutarAccionTurno: vi.fn(),
  reprogramarTurno: vi.fn(),
  listarProfesionales: vi.fn(),
  listarPrestaciones: vi.fn(),
  obtenerHorarios: vi.fn(),
  listarPacientes: vi.fn(),
}));

vi.mock("../../auth/auth", () => ({
  useAuth: () => ({
    request: mocks.request,
    user: {
      sub: "recepcion-1",
      roles: ["recepcion"],
      permisos: ["agenda"],
    },
  }),
}));

vi.mock("../api", () => ({
  consultarAgenda: mocks.consultarAgenda,
  consultarDisponibilidad: mocks.consultarDisponibilidad,
  crearTurno: mocks.crearTurno,
  ejecutarAccionTurno: mocks.ejecutarAccionTurno,
  reprogramarTurno: mocks.reprogramarTurno,
}));

vi.mock("../catalogoApi", () => ({
  listarProfesionales: mocks.listarProfesionales,
  listarPrestaciones: mocks.listarPrestaciones,
  obtenerHorarios: mocks.obtenerHorarios,
}));

vi.mock("../../pacientes/api", () => ({
  listarPacientes: mocks.listarPacientes,
}));

vi.mock("../CancelarTurno", () => ({
  CancelarTurnoButton: ({
    onReprogramar,
  }: {
    onReprogramar?: () => void;
  }) => (
    <>
      <button type="button">Cancelar turno</button>
      <button type="button" onClick={onReprogramar}>
        Continuar con reprogramación
      </button>
    </>
  ),
}));

const turno = {
  id: "turno-1",
  paciente_id: "paciente-1",
  profesional_id: "profesional-1",
  profesional_usuario_id: "odontologo-1",
  prestacion_id: "prestacion-1",
  inicio: "2026-10-09T12:00:00Z",
  fin: "2026-10-09T12:30:00Z",
  estado: "confirmado",
  origen: "mostrador",
  sobreturno: false,
  sobreturno_motivo: null,
  sobreturno_autorizado_por: null,
  senia_id: null,
  cancelled_by: null,
  cancelled_at: null,
  motivo: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.consultarAgenda.mockResolvedValue([turno]);
  mocks.consultarDisponibilidad.mockResolvedValue([]);
  mocks.crearTurno.mockResolvedValue(turno);
  mocks.ejecutarAccionTurno.mockResolvedValue(turno);
  mocks.reprogramarTurno.mockResolvedValue({
    turno_anterior: { ...turno, estado: "reprogramado" },
    turno_nuevo: turno,
  });
  mocks.listarProfesionales.mockResolvedValue([
    {
      id: "profesional-1",
      nombre: "Dra. Demo",
      activo: true,
    },
  ]);
  mocks.listarPrestaciones.mockResolvedValue([
    {
      id: "prestacion-1",
      nombre: "Consulta",
      duracion_min: 30,
      activa: true,
    },
  ]);
  mocks.obtenerHorarios.mockResolvedValue({
    zona_horaria: "America/Argentina/Buenos_Aires",
  });
  mocks.listarPacientes.mockResolvedValue([
    {
      id: "paciente-1",
      nombre: "Paciente",
      apellido: "Demo",
    },
  ]);
});

describe("AgendaPage", () => {
  it("muestra la agenda y permite cambiar a la vista semanal", async () => {
    render(<AgendaPage />);

    expect(await screen.findByText("Demo, Paciente")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Semana" }));

    await waitFor(() => {
      expect(mocks.consultarAgenda).toHaveBeenLastCalledWith(
        mocks.request,
        "semana",
        expect.any(String),
        undefined,
      );
    });
  });

  it("filtra la agenda por profesional seleccionado", async () => {
    render(<AgendaPage />);
    await screen.findByText("Demo, Paciente");

    fireEvent.change(screen.getByLabelText("Profesional"), {
      target: { value: "profesional-1" },
    });

    await waitFor(() => {
      expect(mocks.consultarAgenda).toHaveBeenLastCalledWith(
        mocks.request,
        "dia",
        expect.any(String),
        "profesional-1",
      );
    });
  });

  it("crea turnos con fecha UTC y clave idempotente", async () => {
    vi.stubGlobal("crypto", { randomUUID: () => "idempotency-test" });
    render(<AgendaPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Nuevo turno" }));
    fireEvent.change(screen.getByLabelText("Paciente"), {
      target: { value: "paciente-1" },
    });
    fireEvent.change(screen.getAllByLabelText("Profesional")[1], {
      target: { value: "profesional-1" },
    });
    fireEvent.change(screen.getByLabelText("Prestación"), {
      target: { value: "prestacion-1" },
    });
    fireEvent.change(screen.getByLabelText("Inicio"), {
      target: { value: "2026-10-09T09:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar turno" }));

    await waitFor(() => expect(mocks.crearTurno).toHaveBeenCalledOnce());
    expect(mocks.crearTurno).toHaveBeenCalledWith(
      mocks.request,
      expect.objectContaining({
        paciente_id: "paciente-1",
        profesional_id: "profesional-1",
        inicio: "2026-10-09T12:00:00.000Z",
        fin: "2026-10-09T12:30:00.000Z",
      }),
      "idempotency-test",
    );
    vi.unstubAllGlobals();
  });

  it("deja elegir una alternativa devuelta por el backend ante una colisión", async () => {
    mocks.crearTurno.mockRejectedValue(
      new ApiError(
        {
          code: "RN-AG-03",
          message: "El profesional ya tiene un turno en ese horario.",
          alternativas: ["2026-10-09T12:00:00Z"],
        },
        409,
      ),
    );
    render(<AgendaPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Nuevo turno" }));
    fireEvent.change(screen.getByLabelText("Paciente"), {
      target: { value: "paciente-1" },
    });
    fireEvent.change(screen.getByLabelText("Inicio"), {
      target: { value: "2026-10-09T09:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar turno" }));

    fireEvent.click(await screen.findByRole("button", { name: /09:00/ }));
    expect(screen.getByLabelText("Inicio")).toHaveValue("2026-10-09T09:00");
  });

  it("registra sobreturnos solo con un motivo explícito", async () => {
    render(<AgendaPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Nuevo turno" }));
    fireEvent.change(screen.getByLabelText("Paciente"), {
      target: { value: "paciente-1" },
    });
    fireEvent.click(screen.getByLabelText("Registrar como sobreturno"));
    fireEvent.change(screen.getByLabelText("Motivo del sobreturno"), {
      target: { value: "Urgencia clínica" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar turno" }));

    await waitFor(() => expect(mocks.crearTurno).toHaveBeenCalledOnce());
    expect(mocks.crearTurno.mock.calls[0]?.[1]).toMatchObject({
      sobreturno: true,
      sobreturno_motivo: "Urgencia clínica",
    });
  });

  it("permite iniciar y guardar una reprogramación desde la acción de cancelación", async () => {
    mocks.consultarDisponibilidad.mockResolvedValue(["2026-10-09T13:00:00Z"]);
    render(<AgendaPage />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Continuar con reprogramación" }),
    );
    const nuevoInicio = await screen.findByLabelText("Nuevo inicio");
    fireEvent.click(await screen.findByRole("button", { name: "10:00" }));
    expect(nuevoInicio).toHaveValue("2026-10-09T10:00");
    fireEvent.click(screen.getByRole("button", { name: "Guardar reprogramación" }));

    await waitFor(() => {
      expect(mocks.reprogramarTurno).toHaveBeenCalledWith(
        mocks.request,
        "turno-1",
        {
          profesional_id: "profesional-1",
          prestacion_id: "prestacion-1",
          inicio: "2026-10-09T13:00:00.000Z",
          fin: "2026-10-09T13:30:00.000Z",
        },
      );
    });
    await waitFor(() => expect(mocks.consultarAgenda).toHaveBeenCalledTimes(2));
  });

  it("mantiene el estado guardado y muestra error si falla una acción", async () => {
    mocks.ejecutarAccionTurno.mockRejectedValue(
      new ApiError(
        { code: "RN-AG-08", message: "El estado no permite esta acción." },
        409,
      ),
    );
    render(<AgendaPage />);

    expect(await screen.findByText("Confirmado")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Presente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El estado no permite esta acción.",
    );
    expect(screen.getByText("Confirmado")).toBeInTheDocument();
    expect(screen.queryByText("Presente", { selector: "span" })).not.toBeInTheDocument();
  });
});
