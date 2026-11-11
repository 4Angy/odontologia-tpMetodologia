import { useEffect, useState } from "react";

import { useAuth } from "../auth/auth";
import { getConsumo, type ConsumoItem } from "../notificaciones/api";

const PLAN_PRICE_ARS_CENTS = Number(
  (import.meta as any).env?.VITE_PLAN_PRICE_ARS_CENTS ?? 2990000,
);

const FUERA_DE_ALCANCE: string[] = [
  "Odontograma FDI y periodontograma (v2+)",
  "Facturación electrónica AFIP/ARCA (v1 = caja manual)",
  "Obras sociales / prepagas",
  "Reportes y analytics avanzados",
  "Cobro online completo más allá de la seña por Mercado Pago",
  "Multi-sucursal",
  "API pública",
];

function formatearARS(centavos: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  }).format(centavos / 100);
}

export function TransparenciaPage(): JSX.Element {
  const { request } = useAuth();
  const [items, setItems] = useState<ConsumoItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hoy = new Date().toISOString().slice(0, 10);
    const desde = new Date();
    desde.setDate(desde.getDate() - 30);
    void getConsumo(request, desde.toISOString().slice(0, 10), hoy)
      .then((data) => setItems(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar el consumo."));
  }, [request]);

  const totalMensajes = items.reduce((acc, i) => acc + i.cantidad, 0);
  const totalCosto = items.reduce((acc, i) => acc + i.costo_centavos, 0);

  return (
    <main aria-labelledby="transparencia-title">
      <h1 id="transparencia-title">Transparencia</h1>

      <section aria-labelledby="precio-title">
        <h2 id="precio-title">Precio del plan</h2>
        <p>{formatearARS(PLAN_PRICE_ARS_CENTS)} / mes</p>
      </section>

      <section aria-labelledby="consumo-title">
        <h2 id="consumo-title">Consumo de WhatsApp</h2>
        {error && <p role="alert">{error}</p>}
        <p>
          Total mensajes: {totalMensajes} · Costo: {formatearARS(totalCosto)}
        </p>
      </section>

      <section aria-labelledby="fuera-title">
        <h2 id="fuera-title">Qué no hace (aún)</h2>
        <ul>
          {FUERA_DE_ALCANCE.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}