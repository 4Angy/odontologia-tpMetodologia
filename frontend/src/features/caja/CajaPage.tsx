import { useEffect, useState } from "react";

import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";

interface Cobro {
  id: string;
  paciente_id: string;
  monto_cents: number;
  medio: string;
  concepto: string;
  fecha: string;
}

interface Deuda {
  paciente_id: string;
  nombre: string;
  apellido: string;
  saldo_cents: number;
}

interface Cierre {
  id: string;
  fecha: string;
  total_efectivo_cents: number;
  total_transferencia_cents: number;
  total_mp_cents: number;
  total_otro_cents: number;
}

function mostrarError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : "No se pudo completar la operación. Probá de nuevo.";
}

export function CajaPage(): JSX.Element {
  const { request } = useAuth();
  const [cobros, setCobros] = useState<Cobro[]>([]);
  const [deudas, setDeudas] = useState<Deuda[]>([]);
  const [cierre, setCierre] = useState<Cierre | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    paciente_id: "",
    monto_cents: "",
    medio: "efectivo",
    concepto: "",
  });

  async function cargar(): Promise<void> {
    try {
      const [listaCobros, listaDeudas] = await Promise.all([
        request<Cobro[]>("/cobros"),
        request<Deuda[]>("/deudas"),
      ]);
      setCobros(listaCobros);
      setDeudas(listaDeudas);
      setError(null);
    } catch (err) {
      setError(mostrarError(err));
    }
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function registrarCobro(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    try {
      await request("/cobros", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paciente_id: form.paciente_id.trim(),
          monto_cents: Number(form.monto_cents),
          medio: form.medio,
          concepto: form.concepto.trim(),
        }),
      });
      setForm({ paciente_id: "", monto_cents: "", medio: "efectivo", concepto: "" });
      setMensaje("Cobro registrado.");
      await cargar();
    } catch (err) {
      setError(mostrarError(err));
    }
  }

  async function cerrarCaja(): Promise<void> {
    try {
      const resultado = await request<Cierre>("/caja/cierre-dia", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setCierre(resultado);
      setMensaje("Caja cerrada correctamente.");
      await cargar();
    } catch (err) {
      setError(mostrarError(err));
    }
  }

  return (
    <section>
      <h1>Caja</h1>
      <p>
        v1 es caja manual: el sistema no emite comprobantes fiscales ni integra
        AFIP/ARCA.
      </p>

      {mensaje ? <p role="status">{mensaje}</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <form onSubmit={registrarCobro}>
        <h2>Cobro rápido</h2>
        <label>
          Paciente (ID)
          <input
            value={form.paciente_id}
            onChange={(e) => setForm({ ...form, paciente_id: e.target.value })}
            required
          />
        </label>
        <label>
          Monto (centavos)
          <input
            type="number"
            min={0}
            value={form.monto_cents}
            onChange={(e) => setForm({ ...form, monto_cents: e.target.value })}
            required
          />
        </label>
        <label>
          Medio
          <select
            value={form.medio}
            onChange={(e) => setForm({ ...form, medio: e.target.value })}
          >
            <option value="efectivo">Efectivo</option>
            <option value="transferencia">Transferencia</option>
            <option value="mp">Mercado Pago</option>
            <option value="otro">Otro</option>
          </select>
        </label>
        <label>
          Concepto
          <input
            value={form.concepto}
            onChange={(e) => setForm({ ...form, concepto: e.target.value })}
            required
          />
        </label>
        <button type="submit">Registrar cobro</button>
      </form>

      <section>
        <h2>Deudas</h2>
        {deudas.length === 0 ? (
          <p>Sin deudas pendientes.</p>
        ) : (
          <ul>
            {deudas.map((deuda) => (
              <li key={deuda.paciente_id}>
                {deuda.nombre} {deuda.apellido}: {deuda.saldo_cents} centavos
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Cobros registrados</h2>
        {cobros.length === 0 ? (
          <p>Sin cobros.</p>
        ) : (
          <ul>
            {cobros.map((cobro) => (
              <li key={cobro.id}>
                {cobro.concepto} — {cobro.monto_cents} centavos ({cobro.medio})
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Cierre del día</h2>
        <button type="button" onClick={cerrarCaja}>
          Cerrar caja
        </button>
        {cierre ? (
          <div>
            <p>Efectivo: {cierre.total_efectivo_cents}</p>
            <p>Transferencia: {cierre.total_transferencia_cents}</p>
            <p>Mercado Pago: {cierre.total_mp_cents}</p>
            <p>Otro: {cierre.total_otro_cents}</p>
          </div>
        ) : null}
      </section>
    </section>
  );
}