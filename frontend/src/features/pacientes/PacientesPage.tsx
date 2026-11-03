import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";
import {
  actualizarOptIn,
  actualizarPaciente,
  actualizarEstadoPresupuesto,
  crearEvolucion,
  crearPaciente,
  crearPresupuesto,
  eliminarPresupuesto,
  exportarPacientes,
  listarAdjuntos,
  listarEvoluciones,
  importarPacientes,
  listarOptIns,
  listarPacientes,
  listarPresupuestos,
  obtenerDescargaAdjunto,
  obtenerPaciente,
  subirAdjunto,
} from "./api";
import type {
  Adjunto,
  Evolucion,
  OptIn,
  Paciente,
  PacienteInput,
  Presupuesto,
  ReporteImportacion,
} from "./api";

function mostrarError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : "No se pudo completar la operación. Probá de nuevo.";
}

function valoresFormulario(formulario: HTMLFormElement): PacienteInput {
  const datos = new FormData(formulario);
  const opcional = (campo: string): string | null => {
    const valor = datos.get(campo);
    return typeof valor === "string" && valor.trim() !== "" ? valor.trim() : null;
  };
  return {
    nombre: String(datos.get("nombre") ?? "").trim(),
    apellido: String(datos.get("apellido") ?? "").trim(),
    dni: opcional("dni"),
    telefono: opcional("telefono"),
    email: opcional("email"),
    notas: opcional("notas"),
  };
}

export function PacientesPage(): JSX.Element {
  const { pacienteId } = useParams<{ pacienteId: string }>();
  const { request, requestText, user } = useAuth();
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [optIns, setOptIns] = useState<OptIn[]>([]);
  const [evoluciones, setEvoluciones] = useState<Evolucion[]>([]);
  const [adjuntos, setAdjuntos] = useState<Adjunto[]>([]);
  const [presupuestos, setPresupuestos] = useState<Presupuesto[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [archivoAdjunto, setArchivoAdjunto] = useState<File | null>(null);
  const [reporte, setReporte] = useState<ReporteImportacion | null>(null);
  const [versionTexto, setVersionTexto] = useState("");
  const [consentimientoConfirmado, setConsentimientoConfirmado] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const roles = user?.roles ?? [];
  const puedeEditar = roles.some((rol) => rol === "recepcion" || rol === "dueno");
  const puedeVerClinica = roles.some((rol) => rol === "odontologo" || rol === "dueno");
  const puedeEditarClinica = roles.includes("odontologo");
  const puedeVerPresupuestos = roles.some(
    (rol) => rol === "recepcion" || rol === "odontologo" || rol === "dueno",
  );
  const puedeEditarPresupuestos = roles.some(
    (rol) => rol === "odontologo" || rol === "dueno",
  );

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    const cargar = pacienteId === undefined
      ? listarPacientes(request, "").then((items) => {
          if (vigente) setPacientes(items);
        })
      : Promise.all([
          obtenerPaciente(request, pacienteId),
          listarOptIns(request, pacienteId),
          listarPresupuestos(request, pacienteId),
          puedeVerClinica
            ? Promise.all([
                listarEvoluciones(request, pacienteId),
                listarAdjuntos(request, pacienteId),
              ])
            : Promise.resolve([[], []] as [Evolucion[], Adjunto[]]),
        ]).then(([detalle, preferencias, listaPresupuestos, datosClinicos]) => {
          if (!vigente) return;
          setPaciente(detalle);
          setOptIns(preferencias);
          setPresupuestos(listaPresupuestos);
          setEvoluciones(datosClinicos[0]);
          setAdjuntos(datosClinicos[1]);
        });
    void cargar
      .catch((loadError: unknown) => {
        if (vigente) setError(mostrarError(loadError));
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [pacienteId, puedeVerClinica, request]);

  async function buscar(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    setCargando(true);
    setError(null);
    try {
      setPacientes(await listarPacientes(request, busqueda));
    } catch (searchError: unknown) {
      setError(mostrarError(searchError));
    } finally {
      setCargando(false);
    }
  }

  async function crear(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    const formulario = ev.currentTarget;
    const input = valoresFormulario(formulario);
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const creado = await crearPaciente(request, input);
      setPacientes((actuales) =>
        [...actuales, creado].sort((a, b) =>
          `${a.apellido} ${a.nombre}`.localeCompare(`${b.apellido} ${b.nombre}`),
        ),
      );
      formulario.reset();
      setMensaje("Paciente creado.");
    } catch (createError: unknown) {
      setError(mostrarError(createError));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarPaciente(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (pacienteId === undefined) return;
    const input = valoresFormulario(ev.currentTarget);
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const actualizado = await actualizarPaciente(
        request,
        pacienteId,
        input,
      );
      setPaciente(actualizado);
      if (paciente?.telefono !== actualizado.telefono) {
        setOptIns(await listarOptIns(request, pacienteId));
        setMensaje("Datos actualizados. Si cambió el teléfono, el opt-in de WhatsApp fue revocado.");
      } else {
        setMensaje("Datos actualizados.");
      }
    } catch (updateError: unknown) {
      setError(mostrarError(updateError));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarOptIn(canal: OptIn["canal"], estado: boolean): Promise<void> {
    if (pacienteId === undefined) return;
    if (estado && (!consentimientoConfirmado || versionTexto.trim() === "")) {
      setError("Confirmá el consentimiento explícito e indicá la versión del texto presentado.");
      return;
    }
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const actualizado = await actualizarOptIn(
        request,
        pacienteId,
        canal,
        estado,
        estado ? versionTexto.trim() : undefined,
      );
      setOptIns((actuales) => [
        ...actuales.filter((optIn) => optIn.canal !== canal),
        actualizado,
      ]);
      setMensaje(estado ? "Consentimiento registrado." : "Preferencia revocada.");
    } catch (optInError: unknown) {
      setError(mostrarError(optInError));
    } finally {
      setGuardando(false);
    }
  }

  async function importar(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (archivo === null) return;
    setGuardando(true);
    setError(null);
    setReporte(null);
    try {
      const resultado = await importarPacientes(request, archivo);
      setReporte(resultado);
      setPacientes(await listarPacientes(request, busqueda));
    } catch (importError: unknown) {
      setError(mostrarError(importError));
    } finally {
      setGuardando(false);
    }
  }

  async function exportar(): Promise<void> {
    setError(null);
    try {
      const csv = await exportarPacientes(requestText);
      const href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = href;
      link.download = "pacientes.csv";
      link.click();
      URL.revokeObjectURL(href);
    } catch (exportError: unknown) {
      setError(mostrarError(exportError));
    }
  }

  async function guardarEvolucion(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (pacienteId === undefined) return;
    const form = ev.currentTarget;
    const datos = new FormData(form);
    const slotValue = String(datos.get("pieza_fdi_slot") ?? "");
    const numberValue = String(datos.get("pieza_fdi_numero") ?? "").trim();
    if ((slotValue === "") !== (numberValue === "")) {
      setError("Completá juntos el tipo y el número de la pieza FDI, o dejá ambos vacíos.");
      return;
    }
    const rawFecha = String(datos.get("fecha") ?? "");
    const rawNumber = numberValue === "" ? null : Number(numberValue);
    if (rawNumber !== null && (!Number.isInteger(rawNumber) || rawNumber < 1 || rawNumber > 32)) {
      setError("El número FDI debe ser un entero entre 1 y 32.");
      return;
    }
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const creado = await crearEvolucion(request, pacienteId, {
        motivo: String(datos.get("motivo") ?? "").trim(),
        detalle: String(datos.get("detalle") ?? "").trim(),
        ...(rawFecha !== "" ? { fecha: new Date(rawFecha).toISOString() } : {}),
        pieza_fdi_slot: slotValue === "" ? null : slotValue as Evolucion["pieza_fdi_slot"],
        pieza_fdi_numero: rawNumber,
        odontograma_ref: null,
        firma_simple: datos.get("firma_simple") === "on",
      });
      setEvoluciones((actuales) =>
        [...actuales, creado].sort(
          (a, b) => Date.parse(b.fecha) - Date.parse(a.fecha),
        ),
      );
      form.reset();
      setMensaje("Evolución clínica guardada.");
    } catch (saveError: unknown) {
      setError(mostrarError(saveError));
    } finally {
      setGuardando(false);
    }
  }

  async function cargarAdjunto(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (pacienteId === undefined || archivoAdjunto === null) return;
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const nuevo = await subirAdjunto(request, pacienteId, archivoAdjunto);
      setAdjuntos((actuales) => [nuevo, ...actuales]);
      setArchivoAdjunto(null);
      ev.currentTarget.reset();
      setMensaje("Adjunto clínico guardado de forma privada.");
    } catch (uploadError: unknown) {
      setError(mostrarError(uploadError));
    } finally {
      setGuardando(false);
    }
  }

  async function descargarAdjunto(adjunto: Adjunto): Promise<void> {
    if (pacienteId === undefined) return;
    setError(null);
    try {
      const descarga = await obtenerDescargaAdjunto(request, pacienteId, adjunto.id);
      window.open(descarga.url, "_blank", "noopener,noreferrer");
    } catch (downloadError: unknown) {
      setError(mostrarError(downloadError));
    }
  }

  async function guardarPresupuesto(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    if (pacienteId === undefined) return;
    const form = ev.currentTarget;
    const datos = new FormData(form);
    const monto = Number(String(datos.get("monto_cents") ?? ""));
    if (!Number.isSafeInteger(monto) || monto < 0 || monto > 2_147_483_647) {
      setError("Ingresá un importe válido en centavos.");
      return;
    }
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const creado = await crearPresupuesto(request, pacienteId, {
        items: [{
          descripcion: String(datos.get("descripcion") ?? "").trim(),
          monto_cents: monto,
        }],
        notas: null,
      });
      setPresupuestos((actuales) => [creado, ...actuales]);
      setPaciente(await obtenerPaciente(request, pacienteId));
      form.reset();
      setMensaje("Presupuesto creado en borrador.");
    } catch (saveError: unknown) {
      setError(mostrarError(saveError));
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarEstadoPresupuesto(
    presupuesto: Presupuesto,
    estado: Presupuesto["estado"],
  ): Promise<void> {
    if (pacienteId === undefined) return;
    setGuardando(true);
    setError(null);
    try {
      const actualizado = await actualizarEstadoPresupuesto(
        request,
        pacienteId,
        presupuesto.id,
        estado,
      );
      setPresupuestos((actuales) =>
        actuales.map((item) => item.id === actualizado.id ? actualizado : item),
      );
      setPaciente(await obtenerPaciente(request, pacienteId));
    } catch (updateError: unknown) {
      setError(mostrarError(updateError));
    } finally {
      setGuardando(false);
    }
  }

  async function borrarPresupuesto(presupuesto: Presupuesto): Promise<void> {
    if (pacienteId === undefined) return;
    setGuardando(true);
    setError(null);
    try {
      await eliminarPresupuesto(request, pacienteId, presupuesto.id);
      setPresupuestos((actuales) => actuales.filter((item) => item.id !== presupuesto.id));
      setPaciente(await obtenerPaciente(request, pacienteId));
      setMensaje("Presupuesto eliminado y saldo recalculado.");
    } catch (deleteError: unknown) {
      setError(mostrarError(deleteError));
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) return <p role="status">Cargando pacientes…</p>;

  return pacienteId === undefined ? (
    <section aria-labelledby="titulo-pacientes">
      <h2 id="titulo-pacientes">Pacientes</h2>
      {error !== null && <p role="alert">{error}</p>}
      {mensaje !== null && <p role="status">{mensaje}</p>}

      <form onSubmit={buscar}>
        <label htmlFor="busqueda-pacientes">Buscar por apellido, teléfono o DNI</label>
        <input
          id="busqueda-pacientes"
          value={busqueda}
          onChange={(ev) => setBusqueda(ev.target.value)}
        />
        <button type="submit">Buscar pacientes</button>
      </form>

      {pacientes.length === 0 ? (
        <p>No hay pacientes para mostrar.</p>
      ) : (
        <ul aria-label="Resultados de pacientes">
          {pacientes.map((item) => (
            <li key={item.id}>
              <Link to={`/pacientes/${encodeURIComponent(item.id)}`}>
                {item.nombre} {item.apellido}
              </Link>
              {item.telefono !== null && <span> · {item.telefono}</span>}
            </li>
          ))}
        </ul>
      )}

      {puedeEditar && (
        <form onSubmit={(ev) => void crear(ev)}>
          <h3>Alta de paciente</h3>
          <CamposPaciente disabled={guardando} />
          <button type="submit" disabled={guardando}>Guardar paciente</button>
        </form>
      )}

      {puedeEditar && (
        <ImportarCsv
          archivo={archivo}
          guardando={guardando}
          reporte={reporte}
          onArchivo={setArchivo}
          onImportar={(ev) => void importar(ev)}
        />
      )}
      <button type="button" onClick={() => void exportar()}>Exportar pacientes CSV</button>
    </section>
  ) : (
    <section aria-labelledby="titulo-detalle-paciente">
      <p><Link to="/pacientes">Volver a pacientes</Link></p>
      {error !== null && <p role="alert">{error}</p>}
      {mensaje !== null && <p role="status">{mensaje}</p>}
      {paciente !== null ? (
        <>
          <h2 id="titulo-detalle-paciente">{paciente.nombre} {paciente.apellido}</h2>
          <form onSubmit={(ev) => void guardarPaciente(ev)}>
            <CamposPaciente paciente={paciente} disabled={!puedeEditar || guardando} />
            {puedeEditar && <button type="submit" disabled={guardando}>Guardar cambios</button>}
          </form>
          <p>Saldo informado por el sistema: {paciente.saldo} centavos</p>
          <section aria-labelledby="titulo-consentimiento">
            <h3 id="titulo-consentimiento">Preferencias de comunicación</h3>
            <p>
              Registrá el consentimiento explícito informado al paciente. Guardamos el canal,
              quién lo registró, la fecha y la versión declarada del texto; esto no determina
              su validez legal.
            </p>
            {(["whatsapp", "email"] as const).map((canal) => {
              const optIn = optIns.find((item) => item.canal === canal);
              return (
                <div key={canal}>
                  <h4>{canal === "whatsapp" ? "WhatsApp" : "Email"}</h4>
                  <p>{optIn?.estado ? "Activo" : "Inactivo"}</p>
                  {optIn?.consentimiento_version && (
                    <p>Versión registrada: {optIn.consentimiento_version}</p>
                  )}
                  {puedeEditar && (
                    <button
                      type="button"
                      disabled={guardando}
                      onClick={() => void guardarOptIn(canal, !optIn?.estado)}
                    >
                      {optIn?.estado ? `Revocar ${canal}` : `Activar ${canal}`}
                    </button>
                  )}
                </div>
              );
            })}
            {puedeEditar && (
              <>
                <label htmlFor="version-consentimiento">Versión del texto presentado</label>
                <input
                  id="version-consentimiento"
                  value={versionTexto}
                  onChange={(ev) => setVersionTexto(ev.target.value)}
                  maxLength={80}
                />
                <label>
                  <input
                    type="checkbox"
                    checked={consentimientoConfirmado}
                    onChange={(ev) => setConsentimientoConfirmado(ev.target.checked)}
                  />
                  Confirmo que el paciente dio su consentimiento explícito.
                </label>
              </>
            )}
          </section>
          {puedeVerClinica && (
            <>
              <section aria-labelledby="titulo-evoluciones-clinicas">
                <h3 id="titulo-evoluciones-clinicas">Evoluciones clínicas</h3>
                <p>
                  La firma simple registra autoría e instante; no es firma digital
                  conforme a la Ley 25.506.
                </p>
                {evoluciones.length === 0 ? (
                  <p>No hay evoluciones clínicas registradas.</p>
                ) : (
                  <ol aria-label="Timeline de evoluciones">
                    {evoluciones.map((evolucion) => (
                      <li key={evolucion.id}>
                        <time dateTime={evolucion.fecha}>
                          {new Date(evolucion.fecha).toLocaleString("es-AR", {
                            timeZone: "UTC",
                          })} UTC
                        </time>
                        <h4>{evolucion.motivo}</h4>
                        <p>{evolucion.detalle}</p>
                        {evolucion.pieza_fdi_slot !== null && (
                          <p>
                            Referencia FDI: {evolucion.pieza_fdi_slot}{" "}
                            {evolucion.pieza_fdi_numero}
                          </p>
                        )}
                        {evolucion.firma_simple && (
                          <p>{evolucion.alcance_firma}</p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
                {puedeEditarClinica && (
                  <form onSubmit={(event) => void guardarEvolucion(event)}>
                    <h4>Registrar evolución</h4>
                    <label htmlFor="evolucion-fecha">Fecha y hora (opcional)</label>
                    <input id="evolucion-fecha" name="fecha" type="datetime-local" />
                    <label htmlFor="evolucion-motivo">Motivo</label>
                    <input id="evolucion-motivo" name="motivo" required maxLength={200} />
                    <label htmlFor="evolucion-detalle">Detalle clínico</label>
                    <textarea id="evolucion-detalle" name="detalle" required />
                    <label htmlFor="pieza-fdi-slot">Tipo de ancla FDI (opcional)</label>
                    <select id="pieza-fdi-slot" name="pieza_fdi_slot" defaultValue="">
                      <option value="">Sin pieza</option>
                      <option value="dent">Dentición</option>
                      <option value="face">Cara</option>
                      <option value="tooth">Pieza</option>
                      <option value="zone">Zona</option>
                    </select>
                    <label htmlFor="pieza-fdi-numero">Número FDI</label>
                    <input
                      id="pieza-fdi-numero"
                      name="pieza_fdi_numero"
                      type="number"
                      min={1}
                      max={32}
                      step={1}
                    />
                    <label>
                      <input name="firma_simple" type="checkbox" />
                      Registrar firma simple (no firma digital)
                    </label>
                    <button type="submit" disabled={guardando}>
                      Guardar evolución
                    </button>
                  </form>
                )}
              </section>
              <section aria-labelledby="titulo-adjuntos-clinicos">
                <h3 id="titulo-adjuntos-clinicos">Adjuntos clínicos</h3>
                <p>JPEG, PNG o PDF hasta 10 MiB. Los archivos se guardan en privado.</p>
                {adjuntos.length === 0 ? (
                  <p>No hay adjuntos clínicos.</p>
                ) : (
                  <ul aria-label="Adjuntos clínicos">
                    {adjuntos.map((adjunto) => (
                      <li key={adjunto.id}>
                        <span>{adjunto.nombre}</span>
                        <button
                          type="button"
                          disabled={guardando}
                          onClick={() => void descargarAdjunto(adjunto)}
                        >
                          Descargar {adjunto.nombre}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {puedeEditarClinica && (
                  <form onSubmit={(event) => void cargarAdjunto(event)}>
                    <label htmlFor="archivo-adjunto-clinico">Archivo clínico</label>
                    <input
                      id="archivo-adjunto-clinico"
                      type="file"
                      accept="image/jpeg,image/png,application/pdf"
                      onChange={(event) =>
                        setArchivoAdjunto(event.target.files?.[0] ?? null)
                      }
                    />
                    <button
                      type="submit"
                      disabled={guardando || archivoAdjunto === null}
                    >
                      Guardar adjunto
                    </button>
                  </form>
                )}
              </section>
            </>
          )}
          {puedeVerPresupuestos && (
            <section aria-labelledby="titulo-presupuestos">
              <h3 id="titulo-presupuestos">Presupuestos y saldo</h3>
              <p>
                Saldo derivado:{" "}
                {(paciente.saldo ?? 0).toLocaleString("es-AR")} centavos
              </p>
              {presupuestos.length === 0 ? (
                <p>No hay presupuestos registrados.</p>
              ) : (
                <ul aria-label="Presupuestos">
                  {presupuestos.map((presupuesto) => (
                    <li key={presupuesto.id}>
                      <h4>Presupuesto {presupuesto.estado}</h4>
                      <p>
                        Total: {presupuesto.total_cents.toLocaleString("es-AR")} centavos
                      </p>
                      <ul>
                        {presupuesto.items.map((item) => (
                          <li key={item.id}>
                            {item.descripcion}: {item.monto_cents.toLocaleString("es-AR")} centavos
                          </li>
                        ))}
                      </ul>
                      {puedeEditarPresupuestos && (
                        <>
                          {presupuesto.estado === "borrador" && (
                            <>
                              <button
                                type="button"
                                disabled={guardando}
                                onClick={() =>
                                  void cambiarEstadoPresupuesto(presupuesto, "aprobado")
                                }
                              >
                                Aprobar presupuesto
                              </button>
                              <button
                                type="button"
                                disabled={guardando}
                                onClick={() =>
                                  void cambiarEstadoPresupuesto(presupuesto, "aceptado")
                                }
                              >
                                Marcar presupuesto aceptado
                              </button>
                            </>
                          )}
                          {presupuesto.estado === "aprobado" && (
                            <button
                              type="button"
                              disabled={guardando}
                              onClick={() =>
                                void cambiarEstadoPresupuesto(presupuesto, "aceptado")
                              }
                            >
                              Marcar presupuesto aceptado
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={guardando}
                            onClick={() => void borrarPresupuesto(presupuesto)}
                          >
                            Eliminar presupuesto
                          </button>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {puedeEditarPresupuestos && (
                <form onSubmit={(event) => void guardarPresupuesto(event)}>
                  <h4>Nuevo presupuesto</h4>
                  <label htmlFor="presupuesto-descripcion">Descripción del ítem</label>
                  <input
                    id="presupuesto-descripcion"
                    name="descripcion"
                    required
                    maxLength={200}
                  />
                  <label htmlFor="presupuesto-monto">Importe en centavos</label>
                  <input
                    id="presupuesto-monto"
                    name="monto_cents"
                    type="number"
                    min={0}
                    max={2_147_483_647}
                    step={1}
                    required
                  />
                  <button type="submit" disabled={guardando}>
                    Crear presupuesto borrador
                  </button>
                </form>
              )}
            </section>
          )}
        </>
      ) : (
        error === null && <p>No se encontró el paciente.</p>
      )}
    </section>
  );
}

interface CamposPacienteProps {
  paciente?: Paciente;
  disabled: boolean;
}

function CamposPaciente({ paciente, disabled }: CamposPacienteProps): JSX.Element {
  return (
    <>
      <label htmlFor="nombre-paciente">Nombre</label>
      <input id="nombre-paciente" name="nombre" defaultValue={paciente?.nombre ?? ""} required disabled={disabled} />
      <label htmlFor="apellido-paciente">Apellido</label>
      <input id="apellido-paciente" name="apellido" defaultValue={paciente?.apellido ?? ""} required disabled={disabled} />
      <label htmlFor="dni-paciente">DNI</label>
      <input id="dni-paciente" name="dni" defaultValue={paciente?.dni ?? ""} disabled={disabled} />
      <label htmlFor="telefono-paciente">Teléfono</label>
      <input id="telefono-paciente" name="telefono" defaultValue={paciente?.telefono ?? ""} disabled={disabled} />
      <label htmlFor="email-paciente">Email</label>
      <input id="email-paciente" name="email" type="email" defaultValue={paciente?.email ?? ""} disabled={disabled} />
      <label htmlFor="notas-paciente">Notas</label>
      <textarea id="notas-paciente" name="notas" defaultValue={paciente?.notas ?? ""} disabled={disabled} />
    </>
  );
}

interface ImportarCsvProps {
  archivo: File | null;
  guardando: boolean;
  reporte: ReporteImportacion | null;
  onArchivo: (archivo: File | null) => void;
  onImportar: (event: FormEvent<HTMLFormElement>) => void;
}

function ImportarCsv({
  archivo,
  guardando,
  reporte,
  onArchivo,
  onImportar,
}: ImportarCsvProps): JSX.Element {
  return (
    <section aria-labelledby="titulo-importar-pacientes">
      <h3 id="titulo-importar-pacientes">Importar pacientes</h3>
      <p>CSV UTF-8, hasta 5 MiB y 5.000 filas; columnas nombre, apellido, DNI, teléfono y email.</p>
      <form onSubmit={onImportar}>
        <label htmlFor="archivo-pacientes-csv">Archivo CSV</label>
        <input
          id="archivo-pacientes-csv"
          type="file"
          accept=".csv,text/csv"
          onChange={(ev) => onArchivo(ev.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={archivo === null || guardando}>Importar</button>
      </form>
      {reporte !== null && (
        <div aria-live="polite">
          <p>Importadas: {reporte.importadas}</p>
          <p>Duplicadas: {reporte.duplicadas}</p>
          <p>Fallidas: {reporte.fallidas}</p>
          <ul aria-label="Detalle de importación">
            {reporte.resultados.map((fila) => (
              <li key={fila.fila}>
                Fila {fila.fila}: {fila.estado}
                {fila.mensaje ? ` — ${fila.mensaje}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
