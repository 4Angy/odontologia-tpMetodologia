import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";
import { getConsumo, type ConsumoItem } from "./api";

function formatearARS(centavos: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  }).format(centavos / 100);
}

function hoyISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function hace30DiasISO(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

export function ConsumoPage(): JSX.Element {
  const { request } = useAuth();
  const [desde, setDesde] = useState(hace30DiasISO());
  const [hasta, setHasta] = useState(hoyISO());
  const [items, setItems] = useState<ConsumoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getConsumo(request, desde, hasta);
      setItems(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el consumo.");
    } finally {
      setLoading(false);
    }
  }, [request, desde, hasta]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const totales = useMemo(() => {
    const mensajes = items.reduce((acc, item) => acc + item.cantidad, 0);
    const costo = items.reduce((acc, item) => acc + item.costo_centavos, 0);
    return { mensajes, costo };
  }, [items]);

  return (
    <main aria-labelledby="consumo-title">
      <h1 id="consumo-title">Consumo de notificaciones</h1>
      <p>Costos en centavos, formateados a ARS. Solo lectura.</p>
      <label>
        Desde
        <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
      </label>
      <label>
        Hasta
        <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
      </label>
      <button type="button" onClick={() => void cargar()} disabled={loading}>
        Actualizar
      </button>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Cargando…</p>}
      <p role="status">
        Total mensajes: {totales.mensajes} · Costo: {formatearARS(totales.costo)}
      </p>
      <table>
        <thead>
          <tr>
            <th>Canal</th>
            <th>Estado</th>
            <th>Cantidad</th>
            <th>Costo</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.canal}-${item.estado}-${index}`}>
              <td>{item.canal}</td>
              <td>{item.estado}</td>
              <td>{item.cantidad}</td>
              <td>{formatearARS(item.costo_centavos)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
