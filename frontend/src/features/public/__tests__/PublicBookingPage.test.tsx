import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { PublicBookingPage } from "../PublicBookingPage";

vi.mock("../api", () => ({
  getPublicAvailability: vi.fn().mockResolvedValue({
    tenant_slug: "demo",
    tenant_name: "Consultorio Demo",
    professionals: [{ id: "prof-1", nombre: "Dra. Demo" }],
    services: [{ id: "service-1", nombre: "Consulta", duracion_min: 30 }],
    slots: ["2030-01-02T13:00:00.000Z"],
  }),
  createPublicBooking: vi.fn(),
  confirmPublicBooking: vi.fn().mockResolvedValue({ turno_id: "turn-1", estado: "confirmado" }),
  cancelPublicBooking: vi.fn().mockResolvedValue({ turno_id: "turn-1", estado: "cancelado" }),
  reschedulePublicBooking: vi.fn(),
}));

describe("Página de reserva pública", () => {
  it("muestra catálogo y horario solo después de seleccionar filtros", async () => {
    render(
      <MemoryRouter initialEntries={["/r/demo"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("option", { name: "Dra. Demo" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Profesional"), {
      target: { value: "prof-1" },
    });
    fireEvent.change(screen.getByLabelText("Prestación"), {
      target: { value: "service-1" },
    });

    expect(await screen.findByRole("option", {
      name: /2030/,
    })).toHaveValue("2030-01-02T13:00:00.000Z");
  });

  it("no permite enviar sin horario ni datos requeridos", async () => {
    render(
      <MemoryRouter initialEntries={["/r/demo"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    const submit = screen.getByRole("button", { name: /solicitar turno/i });
    fireEvent.click(submit);
    expect(await screen.findByText(/elegí un horario/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Ana" } });
    expect(screen.getByLabelText("Apellido")).toBeRequired();
    expect(submit).toBeEnabled();
  });

  it("muestra acciones por token y refleja la respuesta del servidor", async () => {
    render(
      <MemoryRouter initialEntries={["/r/demo?token=token-1&accion=confirmar"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Confirmar turno" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Turno confirmado.");
    expect(screen.queryByRole("button", { name: "Cancelar turno" })).not.toBeInTheDocument();
  });
});
