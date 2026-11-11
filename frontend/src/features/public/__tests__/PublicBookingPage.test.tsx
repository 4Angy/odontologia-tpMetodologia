import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  createPublicBooking,
  getPublicAvailability,
  reschedulePublicBooking,
} from "../api";
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

  it("avisa la seña de la prestación y muestra el checkout de Mercado Pago tras reservar", async () => {
    vi.mocked(getPublicAvailability).mockResolvedValue({
      tenant_slug: "demo",
      tenant_name: "Consultorio Demo",
      professionals: [{ id: "prof-1", nombre: "Dra. Demo" }],
      services: [
        {
          id: "service-senia",
          nombre: "Limpieza",
          duracion_min: 30,
          senia_requerida: true,
          senia_monto_cents: 5000,
        },
      ],
      slots: ["2030-01-02T13:00:00.000Z"],
    });
    vi.mocked(createPublicBooking).mockResolvedValue({
      turno_id: "turn-senia",
      estado: "pendiente_confirmacion",
      action_tokens: {},
      checkout_url: "https://mp.test/checkout",
    });

    render(
      <MemoryRouter initialEntries={["/r/demo"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Profesional"), {
      target: { value: "prof-1" },
    });
    fireEvent.change(screen.getByLabelText("Prestación"), {
      target: { value: "service-senia" },
    });
    expect(await screen.findByRole("note")).toHaveTextContent(/requiere una seña de 50 /i);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Ana" } });
    fireEvent.change(screen.getByLabelText("Apellido"), { target: { value: "Perez" } });
    fireEvent.change(screen.getByLabelText(/horario/i), {
      target: { value: "2030-01-02T13:00:00.000Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: /solicitar turno/i }));

    expect(await screen.findByRole("link", { name: /pagar seña/i })).toHaveAttribute(
      "href",
      "https://mp.test/checkout",
    );
    expect(screen.getByText(/pagá la seña/i)).toBeInTheDocument();
  });

  it("reprograma avisando el arrastre de la seña acreditada", async () => {
    vi.mocked(reschedulePublicBooking).mockResolvedValue({
      turno_id: "turn-2",
      estado: "pendiente_confirmacion",
      action_tokens: {},
      checkout_url: null,
    });

    render(
      <MemoryRouter initialEntries={["/r/demo?token=token-1&accion=reprogramar"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Profesional"), {
      target: { value: "prof-1" },
    });
    fireEvent.change(screen.getByLabelText("Prestación"), {
      target: { value: "service-1" },
    });
    fireEvent.change(screen.getByLabelText(/horario/i), {
      target: { value: "2030-01-02T13:00:00.000Z" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /reprogramar turno/i })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /reprogramar turno/i }));

    expect(await screen.findByText(/se arrastra al nuevo turno/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /pagar seña/i })).not.toBeInTheDocument();
  });

  it("reprograma pidiendo el pago de la seña pendiente", async () => {
    vi.mocked(reschedulePublicBooking).mockResolvedValue({
      turno_id: "turn-2",
      estado: "pendiente_confirmacion",
      action_tokens: {},
      checkout_url: "https://mp.test/reintento",
    });

    render(
      <MemoryRouter initialEntries={["/r/demo?token=token-1&accion=reprogramar"]}>
        <Routes>
          <Route path="/r/:slug" element={<PublicBookingPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("Profesional"), {
      target: { value: "prof-1" },
    });
    fireEvent.change(screen.getByLabelText("Prestación"), {
      target: { value: "service-1" },
    });
    fireEvent.change(screen.getByLabelText(/horario/i), {
      target: { value: "2030-01-02T13:00:00.000Z" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /reprogramar turno/i })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /reprogramar turno/i }));

    expect(await screen.findByRole("link", { name: /pagar seña/i })).toHaveAttribute(
      "href",
      "https://mp.test/reintento",
    );
  });
});
