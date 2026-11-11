export interface Profesional {
  id: string;
  tenant_id: string;
  nombre: string;
  usuario_id: string | null;
  color_agenda: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfesionalInput {
  nombre: string;
  usuario_id: string | null;
  color_agenda: string | null;
  activo: boolean;
}

export interface Prestacion {
  id: string;
  tenant_id: string;
  nombre: string;
  duracion_min: number;
  precio_ref: number | null;
  activa: boolean;
  /** Override de seña por prestación (C-12); null = usa la config global. */
  senia_requerida: boolean | null;
  senia_monto_cents: number | null;
  created_at: string;
  updated_at: string;
}

export interface PrestacionInput {
  nombre: string;
  duracion_min: number;
  precio_ref: number | null;
  activa: boolean;
  senia_requerida: boolean | null;
  senia_monto_cents: number | null;
}

export interface Bloqueo {
  id: string;
  tenant_id: string;
  profesional_id: string;
  inicio: string;
  fin: string;
  motivo: string | null;
  created_at: string;
  updated_at: string;
}

export interface BloqueoInput {
  profesional_id: string;
  inicio: string;
  fin: string;
  motivo: string | null;
}

export type PoliticaDevolucionSenia = "no_devuelve" | "devuelve_50" | "devuelve_100";

export interface ConfiguracionAgenda {
  antelacion_cancel_hs: number;
  antelacion_reserva_hs: number;
  recordatorio_t_48h: boolean;
  recordatorio_t_24h: boolean;
  politica_devolucion_senia: PoliticaDevolucionSenia;
}

export interface HorarioSemanal {
  id?: string;
  dia_semana: number;
  inicio: string;
  fin: string;
}

export interface HorariosSemana {
  profesional_id: string;
  zona_horaria: string;
  horarios: HorarioSemanal[];
}

export type CatalogoRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function listarProfesionales(request: CatalogoRequest): Promise<Profesional[]> {
  return request<Profesional[]>("/profesionales");
}

export function guardarProfesional(
  request: CatalogoRequest,
  input: ProfesionalInput,
  id?: string,
): Promise<Profesional> {
  return request<Profesional>(
    id === undefined ? "/profesionales" : `/profesionales/${encodeURIComponent(id)}`,
    json(id === undefined ? "POST" : "PUT", input),
  );
}

export function eliminarProfesional(request: CatalogoRequest, id: string): Promise<void> {
  return request<void>(`/profesionales/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function listarPrestaciones(request: CatalogoRequest): Promise<Prestacion[]> {
  return request<Prestacion[]>("/prestaciones");
}

export function guardarPrestacion(
  request: CatalogoRequest,
  input: PrestacionInput,
  id?: string,
): Promise<Prestacion> {
  return request<Prestacion>(
    id === undefined ? "/prestaciones" : `/prestaciones/${encodeURIComponent(id)}`,
    json(id === undefined ? "POST" : "PUT", input),
  );
}

export function eliminarPrestacion(request: CatalogoRequest, id: string): Promise<void> {
  return request<void>(`/prestaciones/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function listarBloqueos(request: CatalogoRequest): Promise<Bloqueo[]> {
  return request<Bloqueo[]>("/bloqueos");
}

export function crearBloqueo(
  request: CatalogoRequest,
  input: BloqueoInput,
): Promise<Bloqueo> {
  return request<Bloqueo>("/bloqueos", json("POST", input));
}

export function actualizarBloqueo(
  request: CatalogoRequest,
  id: string,
  input: BloqueoInput,
): Promise<Bloqueo> {
  return request<Bloqueo>(
    `/bloqueos/${encodeURIComponent(id)}`,
    json("PUT", input),
  );
}

export function eliminarBloqueo(request: CatalogoRequest, id: string): Promise<void> {
  return request<void>(`/bloqueos/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function obtenerConfiguracion(request: CatalogoRequest): Promise<ConfiguracionAgenda> {
  return request<ConfiguracionAgenda>("/config");
}

export function guardarConfiguracion(
  request: CatalogoRequest,
  input: ConfiguracionAgenda,
): Promise<ConfiguracionAgenda> {
  return request<ConfiguracionAgenda>("/config", json("PUT", input));
}

export function obtenerHorarios(
  request: CatalogoRequest,
  profesionalId: string,
): Promise<HorariosSemana> {
  return request<HorariosSemana>(
    `/profesionales/${encodeURIComponent(profesionalId)}/horarios`,
  );
}

export function guardarHorarios(
  request: CatalogoRequest,
  profesionalId: string,
  horarios: HorarioSemanal[],
): Promise<HorariosSemana> {
  return request<HorariosSemana>(
    `/profesionales/${encodeURIComponent(profesionalId)}/horarios`,
    json("PUT", { horarios }),
  );
}
