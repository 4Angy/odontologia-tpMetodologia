import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";
import { getListaEspera, type ListaEsperaItem } from "./api";

export function ListaEsperaPage(): JSX.Element {
  const { request } = useAuth();
  const [items, setItems] = useState<ListaEsperaItem[]>([]);
  const [estado, setEstado] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getListaEspera(request, estado || undefined);
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de espera.");
    } finally {
      setLoading(false);
    }
  }, [request, estado]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  return (
    <main aria-labelledby="lista-espera-title">
      <h1 id="lista-espera-title">Lista de espera</h1>
      <label>
        Estado
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">todos</option>
          <option value="activa">activa</option>
          <option value="ofrecida">ofrecida</option>
          <option value="convertida">convertida</option>
          <option value="vencida">vencida</option>
        </select>
      </label>
      <button type="button" onClick={() => void cargar()} disabled={loading}>
        Actualizar
      </button>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Cargando...</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            {item.paciente_id} - {item.estado}
          </li>
        ))}
      </ul>
    </main>
  );
}
