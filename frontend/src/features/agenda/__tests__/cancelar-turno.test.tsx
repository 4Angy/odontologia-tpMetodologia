import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CancelarTurnoModal } from "../CancelarTurno";
import type { CancelarTurnoFn } from "../CancelarTurno";

function rnAg01(): { code: string; message: string; action: { type: string; hint: string } } {
  return {
    code: "RN-AG-01",
    message: "No se puede cancelar con menos de 24 h de antelación.",
    action: { type: "reprogramar", hint: "Coordiná manualmente un nuevo horario." },
  };
}

describe("CancelarTurnoModal", () => {
  it("exige motivo: botón deshabilitado sin motivo", () => {
    const cancelar: CancelarTurnoFn = vi.fn();
    render(
      <CancelarTurnoModal turnoId="t-1" abierto={true} onCerrar={() => undefined} cancelarTurno={cancelar} />,
    );
    const boton = screen.getByRole("button", { name: /confirmar cancelación/i });
    expect(boton).toBeDisabled();
    expect(cancelar).not.toHaveBeenCalled();
  });

  it("error RN-AG-01 muestra mensaje español-AR con Reprogramar deshabilitada/informativa", async () => {
    const cancelar: CancelarTurnoFn = vi.fn().mockRejectedValue(rnAg01());
    render(
      <CancelarTurnoModal turnoId="t-1" abierto={true} onCerrar={() => undefined} cancelarTurno={cancelar} />,
    );
    fireEvent.change(screen.getByLabelText(/motivo/i), { target: { value: "Paciente avisa" } });
    fireEvent.click(screen.getByRole("button", { name: /confirmar cancelación/i }));

    await waitFor(() => {
      expect(screen.getByText(/no se puede cancelar con menos de 24 h/i)).toBeInTheDocument();
    });
    const reprogramar = screen.getByRole("button", { name: /reprogramar/i });
    expect(reprogramar).toBeDisabled();
    expect(screen.getByText(/coordiná manualmente/i)).toBeInTheDocument();
  });
});
