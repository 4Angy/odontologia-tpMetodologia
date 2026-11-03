export interface Paciente {
  id: string;
  tenant_id: string;
  nombre: string;
  apellido: string;
  dni: string | null;
  telefono: string | null;
  email: string | null;
  fecha_nac: string | null;
  notas: string | null;
  saldo: number;
  created_at: string;
  updated_at: string;
}

export interface PacienteInput {
  nombre: string;
  apellido: string;
  dni: string | null;
  telefono: string | null;
  email: string | null;
  notas: string | null;
}

export interface OptIn {
  id: string;
  paciente_id: string;
  tenant_id: string;
  canal: "whatsapp" | "email";
  estado: boolean;
  updated_at: string;
  consentimiento_version: string | null;
  consentimiento_actor_id: string | null;
  consentimiento_at: string | null;
}

export interface Evolucion {
  id: string;
  paciente_id: string;
  tenant_id: string;
  profesional_id: string | null;
  fecha: string;
  motivo: string;
  detalle: string;
  pieza_fdi_slot: "dent" | "face" | "tooth" | "zone" | null;
  pieza_fdi_numero: number | null;
  odontograma_ref: string | null;
  firma_simple: boolean;
  firmado_at: string | null;
  alcance_firma: string;
  updated_at: string;
}

export interface EvolucionInput {
  profesional_id?: string;
  fecha?: string;
  motivo: string;
  detalle: string;
  pieza_fdi_slot: Evolucion["pieza_fdi_slot"];
  pieza_fdi_numero: number | null;
  odontograma_ref: string | null;
  firma_simple: boolean;
}

export interface Adjunto {
  id: string;
  paciente_id: string;
  tenant_id: string;
  nombre: string;
  tipo: string;
  tamano_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface AdjuntoDownload {
  url: string;
  expires_in_seconds: number;
}

export interface PresupuestoItem {
  id: string;
  descripcion: string;
  monto_cents: number;
}

export type EstadoPresupuesto = "borrador" | "aprobado" | "aceptado";

export interface Presupuesto {
  id: string;
  paciente_id: string;
  tenant_id: string;
  total_cents: number;
  estado: EstadoPresupuesto;
  notas: string | null;
  items: PresupuestoItem[];
  created_at: string;
  updated_at: string;
}

export interface PresupuestoInput {
  items: Array<{ descripcion: string; monto_cents: number }>;
  notas: string | null;
}

export interface ResultadoImportacion {
  fila: number;
  estado: "importada" | "duplicada" | "fallida";
  paciente_id?: string | null;
  code?: string | null;
  mensaje?: string | null;
}

export interface ReporteImportacion {
  importadas: number;
  duplicadas: number;
  fallidas: number;
  resultados: ResultadoImportacion[];
}

export type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;
export type ApiTextRequest = (path: string, init?: RequestInit) => Promise<string>;

export function listarPacientes(request: ApiRequest, query: string): Promise<Paciente[]> {
  const search = new URLSearchParams();
  if (query.trim() !== "") search.set("q", query.trim());
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return request<Paciente[]>(`/pacientes${suffix}`);
}

export function obtenerPaciente(request: ApiRequest, pacienteId: string): Promise<Paciente> {
  return request<Paciente>(`/pacientes/${encodeURIComponent(pacienteId)}`);
}

export function listarOptIns(request: ApiRequest, pacienteId: string): Promise<OptIn[]> {
  return request<OptIn[]>(`/pacientes/${encodeURIComponent(pacienteId)}/optins`);
}

export function listarEvoluciones(
  request: ApiRequest,
  pacienteId: string,
): Promise<Evolucion[]> {
  return request<Evolucion[]>(
    `/pacientes/${encodeURIComponent(pacienteId)}/evoluciones`,
  );
}

export function crearEvolucion(
  request: ApiRequest,
  pacienteId: string,
  input: EvolucionInput,
): Promise<Evolucion> {
  return request<Evolucion>(
    `/pacientes/${encodeURIComponent(pacienteId)}/evoluciones`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
}

export function actualizarEvolucion(
  request: ApiRequest,
  pacienteId: string,
  evolucionId: string,
  input: EvolucionInput,
): Promise<Evolucion> {
  return request<Evolucion>(
    `/pacientes/${encodeURIComponent(pacienteId)}/evoluciones/${encodeURIComponent(evolucionId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
}

export function listarAdjuntos(
  request: ApiRequest,
  pacienteId: string,
): Promise<Adjunto[]> {
  return request<Adjunto[]>(`/pacientes/${encodeURIComponent(pacienteId)}/adjuntos`);
}

export function subirAdjunto(
  request: ApiRequest,
  pacienteId: string,
  archivo: File,
): Promise<Adjunto> {
  return request<Adjunto>(`/pacientes/${encodeURIComponent(pacienteId)}/adjuntos`, {
    method: "POST",
    headers: {
      "Content-Type": archivo.type,
      "X-Filename": encodeURIComponent(archivo.name),
    },
    body: archivo,
  });
}

export function obtenerDescargaAdjunto(
  request: ApiRequest,
  pacienteId: string,
  adjuntoId: string,
): Promise<AdjuntoDownload> {
  return request<AdjuntoDownload>(
    `/pacientes/${encodeURIComponent(pacienteId)}/adjuntos/${encodeURIComponent(adjuntoId)}/descarga`,
  );
}

export function listarPresupuestos(
  request: ApiRequest,
  pacienteId: string,
): Promise<Presupuesto[]> {
  return request<Presupuesto[]>(
    `/pacientes/${encodeURIComponent(pacienteId)}/presupuestos`,
  );
}

export function crearPresupuesto(
  request: ApiRequest,
  pacienteId: string,
  input: PresupuestoInput,
): Promise<Presupuesto> {
  return request<Presupuesto>(
    `/pacientes/${encodeURIComponent(pacienteId)}/presupuestos`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
}

export function actualizarPresupuesto(
  request: ApiRequest,
  pacienteId: string,
  presupuestoId: string,
  input: PresupuestoInput,
): Promise<Presupuesto> {
  return request<Presupuesto>(
    `/pacientes/${encodeURIComponent(pacienteId)}/presupuestos/${encodeURIComponent(presupuestoId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
}

export function actualizarEstadoPresupuesto(
  request: ApiRequest,
  pacienteId: string,
  presupuestoId: string,
  estado: EstadoPresupuesto,
): Promise<Presupuesto> {
  return request<Presupuesto>(
    `/pacientes/${encodeURIComponent(pacienteId)}/presupuestos/${encodeURIComponent(presupuestoId)}/estado`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado }),
    },
  );
}

export function eliminarPresupuesto(
  request: ApiRequest,
  pacienteId: string,
  presupuestoId: string,
): Promise<void> {
  return request<void>(
    `/pacientes/${encodeURIComponent(pacienteId)}/presupuestos/${encodeURIComponent(presupuestoId)}`,
    { method: "DELETE" },
  );
}

export function crearPaciente(request: ApiRequest, input: PacienteInput): Promise<Paciente> {
  return request<Paciente>("/pacientes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function actualizarPaciente(
  request: ApiRequest,
  pacienteId: string,
  input: PacienteInput,
): Promise<Paciente> {
  return request<Paciente>(`/pacientes/${encodeURIComponent(pacienteId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function actualizarOptIn(
  request: ApiRequest,
  pacienteId: string,
  canal: OptIn["canal"],
  estado: boolean,
  versionTexto?: string,
): Promise<OptIn> {
  return request<OptIn>(`/pacientes/${encodeURIComponent(pacienteId)}/optins`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      canal,
      estado,
      ...(estado && versionTexto !== undefined ? { version_texto: versionTexto } : {}),
    }),
  });
}

export function importarPacientes(
  request: ApiRequest,
  file: File,
): Promise<ReporteImportacion> {
  return request<ReporteImportacion>("/pacientes/import-csv", {
    method: "POST",
    headers: { "Content-Type": "text/csv; charset=utf-8" },
    body: file,
  });
}

export function exportarPacientes(requestText: ApiTextRequest): Promise<string> {
  return requestText("/export/pacientes.csv");
}
