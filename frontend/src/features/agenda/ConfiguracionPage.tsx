import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";
import {
  actualizarBloqueo,
  crearBloqueo,
  eliminarBloqueo,
  eliminarPrestacion,
  eliminarProfesional,
  guardarConfiguracion,
  guardarHorarios,
  guardarPrestacion,
  guardarProfesional,
  listarBloqueos,
  listarPrestaciones,
  listarProfesionales,
  obtenerConfiguracion,
  obtenerHorarios,
} from "./catalogoApi";
import type {
  Bloqueo,
  ConfiguracionAgenda,
  HorarioSemanal,
  Prestacion,
  Profesional,
} from "./catalogoApi";

const CONFIGURACION_DEFAULT: ConfiguracionAgenda = {
  antelacion_cancel_hs: 24,
  antelacion_reserva_hs: 2,
  recordatorio_t_48h: true,
  recordatorio_t_24h: true,
  politica_devolucion_senia: "devuelve_100",
};

const POLITICAS_DEVOLUCION = [
  { valor: "devuelve_100", etiqueta: "100% a favor del paciente" },
  { valor: "devuelve_50", etiqueta: "50% a favor del paciente" },
  { valor: "no_devuelve", etiqueta: "Sin devolución" },
] as const;

function formatearMontos(centavos: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  }).format(centavos / 100);
}

const DIAS_SEMANA = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
];

function mostrarError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : "No se pudo completar la operación. Probá de nuevo.";
}

function tieneOffset(texto: string): boolean {
  return /(?:Z|[+-]\d{2}:\d{2})$/i.test(texto) && !Number.isNaN(Date.parse(texto));
}

function valorOpcional(value: FormDataEntryValue | null): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

export function ConfiguracionPage(): JSX.Element {
  const { request, user } = useAuth();
  const roles = user?.roles ?? [];
  const puedeEditarCatalogo = roles.some((rol) => rol === "recepcion" || rol === "dueno");
  const esDueno = roles.includes("dueno");
  const [profesionales, setProfesionales] = useState<Profesional[]>([]);
  const [prestaciones, setPrestaciones] = useState<Prestacion[]>([]);
  const [bloqueos, setBloqueos] = useState<Bloqueo[]>([]);
  const [configuracion, setConfiguracion] = useState<ConfiguracionAgenda>(CONFIGURACION_DEFAULT);
  const [profesionalEditando, setProfesionalEditando] = useState<string | null>(null);
  const [prestacionEditando, setPrestacionEditando] = useState<string | null>(null);
  const [bloqueoEditando, setBloqueoEditando] = useState<string | null>(null);
  const [nombreProfesional, setNombreProfesional] = useState("");
  const [colorAgenda, setColorAgenda] = useState("");
  const [profesionalUsuarioId, setProfesionalUsuarioId] = useState("");
  const [profesionalActivo, setProfesionalActivo] = useState(true);
  const [nombrePrestacion, setNombrePrestacion] = useState("");
  const [duracion, setDuracion] = useState("30");
  const [precio, setPrecio] = useState("");
  const [prestacionActiva, setPrestacionActiva] = useState(true);
  const [seniaRequerida, setSeniaRequerida] = useState<"global" | "si" | "no">("global");
  const [seniaMonto, setSeniaMonto] = useState("");
  const [profesionalBloqueo, setProfesionalBloqueo] = useState("");
  const [inicioBloqueo, setInicioBloqueo] = useState("");
  const [finBloqueo, setFinBloqueo] = useState("");
  const [motivoBloqueo, setMotivoBloqueo] = useState("");
  const [profesionalHorario, setProfesionalHorario] = useState("");
  const [zonaHoraria, setZonaHoraria] = useState("");
  const [horarios, setHorarios] = useState<HorarioSemanal[]>([]);
  const [diaHorario, setDiaHorario] = useState("0");
  const [inicioHorario, setInicioHorario] = useState("09:00");
  const [finHorario, setFinHorario] = useState("17:00");
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const recargar = useCallback(async (): Promise<void> => {
    const [nuevosProfesionales, nuevasPrestaciones, nuevosBloqueos, nuevaConfiguracion] =
      await Promise.all([
        listarProfesionales(request),
        listarPrestaciones(request),
        listarBloqueos(request),
        obtenerConfiguracion(request),
      ]);
    setProfesionales(nuevosProfesionales);
    setPrestaciones(nuevasPrestaciones);
    setBloqueos(nuevosBloqueos);
    setConfiguracion({ ...CONFIGURACION_DEFAULT, ...nuevaConfiguracion });
  }, [request]);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    void recargar()
      .catch((loadError: unknown) => {
        if (vigente) setError(mostrarError(loadError));
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [recargar]);

  useEffect(() => {
    if (profesionalHorario === "") {
      setHorarios([]);
      setZonaHoraria("");
      return;
    }
    let vigente = true;
    setError(null);
    void obtenerHorarios(request, profesionalHorario)
      .then((respuesta) => {
        if (!vigente) return;
        setHorarios(respuesta.horarios.map(({ dia_semana, inicio, fin }) => ({
          dia_semana,
          inicio: inicio.slice(0, 5),
          fin: fin.slice(0, 5),
        })));
        setZonaHoraria(respuesta.zona_horaria);
      })
      .catch((loadError: unknown) => {
        if (vigente) setError(mostrarError(loadError));
      });
    return () => {
      vigente = false;
    };
  }, [profesionalHorario, request]);

  async function ejecutar(accion: () => Promise<void>, exito: string): Promise<void> {
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      await accion();
      setMensaje(exito);
    } catch (actionError: unknown) {
      setError(mostrarError(actionError));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarProfesionalFormulario(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const input = {
      nombre: nombreProfesional.trim(),
      usuario_id: valorOpcional(profesionalUsuarioId),
      color_agenda: valorOpcional(form.get("color_agenda")),
      activo: profesionalActivo,
    };
    if (input.nombre === "") {
      setError("El nombre del profesional es obligatorio.");
      return;
    }
    const id = profesionalEditando;
    await ejecutar(async () => {
      const guardado = await guardarProfesional(request, input, id ?? undefined);
      await recargar();
      setProfesionalHorario(guardado.id);
      setProfesionalBloqueo(guardado.id);
      setProfesionalEditando(null);
      setNombreProfesional("");
      setColorAgenda("");
      setProfesionalUsuarioId("");
      setProfesionalActivo(true);
    }, id === null ? "Profesional creado." : "Profesional actualizado.");
  }

  async function guardarPrestacionFormulario(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const minutos = Number(duracion);
    const centavos = precio.trim() === "" ? null : Number(precio);
    const seniaCentavos = seniaMonto.trim() === "" ? null : Number(seniaMonto);
    if (
      nombrePrestacion.trim() === "" ||
      !Number.isInteger(minutos) ||
      minutos < 5 ||
      minutos > 240 ||
      (centavos !== null && (!Number.isSafeInteger(centavos) || centavos < 0)) ||
      (seniaCentavos !== null && (!Number.isSafeInteger(seniaCentavos) || seniaCentavos <= 0))
    ) {
      setError("Ingresá nombre, duración entre 5 y 240 minutos e importes en centavos enteros.");
      return;
    }
    if (seniaCentavos !== null && seniaRequerida === "no") {
      setError("Si la prestación no requiere seña, no necesita monto de seña.");
      return;
    }
    const id = prestacionEditando;
    await ejecutar(async () => {
      await guardarPrestacion(request, {
        nombre: nombrePrestacion.trim(),
        duracion_min: minutos,
        precio_ref: centavos,
        activa: prestacionActiva,
        senia_requerida: seniaRequerida === "global" ? null : seniaRequerida === "si",
        senia_monto_cents: seniaCentavos,
      }, id ?? undefined);
      await recargar();
      setPrestacionEditando(null);
      setNombrePrestacion("");
      setDuracion("30");
      setPrecio("");
      setPrestacionActiva(true);
      setSeniaRequerida("global");
      setSeniaMonto("");
    }, id === null ? "Prestación creada." : "Prestación actualizada.");
  }

  async function guardarBloqueo(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!tieneOffset(inicioBloqueo) || !tieneOffset(finBloqueo)) {
      setError("Usá fechas ISO 8601 con zona horaria, por ejemplo 2026-11-02T10:00:00-03:00.");
      return;
    }
    if (Date.parse(finBloqueo) <= Date.parse(inicioBloqueo)) {
      setError("El fin del bloqueo debe ser posterior al inicio.");
      return;
    }
    if (profesionalBloqueo === "") {
      setError("Seleccioná un profesional para el bloqueo.");
      return;
    }
    const id = bloqueoEditando;
    await ejecutar(async () => {
      const input = {
        profesional_id: profesionalBloqueo,
        inicio: inicioBloqueo,
        fin: finBloqueo,
        motivo: motivoBloqueo.trim() || null,
      };
      if (id === null) {
        await crearBloqueo(request, input);
      } else {
        await actualizarBloqueo(request, id, input);
      }
      setBloqueos(await listarBloqueos(request));
      setBloqueoEditando(null);
      setInicioBloqueo("");
      setFinBloqueo("");
      setMotivoBloqueo("");
    }, id === null ? "Bloqueo creado." : "Bloqueo actualizado.");
  }

  async function agregarHorario(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (inicioHorario >= finHorario) {
      setError("El fin del horario debe ser posterior al inicio.");
      return;
    }
    const nuevo: HorarioSemanal = {
      dia_semana: Number(diaHorario),
      inicio: inicioHorario,
      fin: finHorario,
    };
    if (horarios.some((item) =>
      item.dia_semana === nuevo.dia_semana &&
      nuevo.inicio < item.fin &&
      nuevo.fin > item.inicio
    )) {
      setError("Los horarios del mismo día no pueden superponerse.");
      return;
    }
    setError(null);
    setHorarios((actuales) =>
      [...actuales, nuevo].sort((a, b) =>
        a.dia_semana - b.dia_semana || a.inicio.localeCompare(b.inicio),
      ),
    );
  }

  async function guardarConfiguracionFormulario(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const cancellationHours = Number(form.get("antelacion_cancel_hs"));
    const reservationHours = Number(form.get("antelacion_reserva_hs"));
    if (
      !Number.isInteger(cancellationHours) ||
      cancellationHours < 0 ||
      !Number.isInteger(reservationHours) ||
      reservationHours < 0
    ) {
      setError("Las antelaciones deben ser números enteros no negativos.");
      return;
    }
    await ejecutar(async () => {
      const nueva = await guardarConfiguracion(request, {
        antelacion_cancel_hs: cancellationHours,
        antelacion_reserva_hs: reservationHours,
        recordatorio_t_48h: form.get("recordatorio_t_48h") === "on",
        recordatorio_t_24h: form.get("recordatorio_t_24h") === "on",
        politica_devolucion_senia: configuracion.politica_devolucion_senia,
      });
      setConfiguracion(nueva);
    }, "Configuración guardada.");
  }

  if (cargando) return <p role="status">Cargando catálogo y configuración…</p>;

  return (
    <section aria-labelledby="titulo-configuracion">
      <h2 id="titulo-configuracion">Catálogo y configuración</h2>
      {error !== null && <p role="alert">{error}</p>}
      {mensaje !== null && <p role="status">{mensaje}</p>}

      <section aria-labelledby="titulo-profesionales">
        <h3 id="titulo-profesionales">Profesionales</h3>
        {profesionales.length === 0 ? (
          <p>No hay profesionales cargados.</p>
        ) : (
          <ul>
            {profesionales.map((profesional) => (
              <li key={profesional.id}>
                {profesional.nombre} {profesional.activo ? "(activo)" : "(inactivo)"}
                {puedeEditarCatalogo && (
                  <>
                    <button type="button" onClick={() => {
                      setProfesionalEditando(profesional.id);
                      setNombreProfesional(profesional.nombre);
                      setColorAgenda(profesional.color_agenda ?? "");
                      setProfesionalUsuarioId(profesional.usuario_id ?? "");
                      setProfesionalActivo(profesional.activo);
                    }}>Editar</button>
                    <button type="button" disabled={guardando} onClick={() => {
                      void ejecutar(async () => {
                        await eliminarProfesional(request, profesional.id);
                        await recargar();
                      }, "Profesional eliminado.");
                    }}>Eliminar</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        {puedeEditarCatalogo && (
          <form onSubmit={(event) => void guardarProfesionalFormulario(event)}>
            <label>
              Nombre del profesional
              <input
                name="nombre"
                required
                value={nombreProfesional}
                onChange={(event) => setNombreProfesional(event.target.value)}
              />
            </label>
            <label>
              Usuario asociado (opcional)
              <input
                name="usuario_id"
                value={profesionalUsuarioId}
                onChange={(event) => setProfesionalUsuarioId(event.target.value)}
              />
            </label>
            <label>
              Color de agenda (opcional)
              <input
                name="color_agenda"
                value={colorAgenda}
                onChange={(event) => setColorAgenda(event.target.value)}
              />
            </label>
            <label>
              Activo
              <input
                name="activo"
                type="checkbox"
                checked={profesionalActivo}
                onChange={(event) => setProfesionalActivo(event.target.checked)}
              />
            </label>
            <button type="submit" disabled={guardando}>
              {profesionalEditando === null ? "Guardar profesional" : "Actualizar profesional"}
            </button>
            {profesionalEditando !== null && (
              <button type="button" onClick={() => {
                setProfesionalEditando(null);
                setNombreProfesional("");
                setColorAgenda("");
                setProfesionalUsuarioId("");
                setProfesionalActivo(true);
              }}>Cancelar edición</button>
            )}
          </form>
        )}
      </section>

      <section aria-labelledby="titulo-prestaciones">
        <h3 id="titulo-prestaciones">Prestaciones</h3>
        {prestaciones.length === 0 ? (
          <p>No hay prestaciones cargadas.</p>
        ) : (
          <ul>
            {prestaciones.map((prestacion) => (
              <li key={prestacion.id}>
                {prestacion.nombre} — {prestacion.duracion_min} min
                {prestacion.precio_ref === null ? "" : ` — ${formatearMontos(prestacion.precio_ref)}`}
                {prestacion.senia_monto_cents === null
                  ? ""
                  : ` — seña ${formatearMontos(prestacion.senia_monto_cents)}${
                      prestacion.senia_requerida === null
                        ? " (según config.)"
                        : prestacion.senia_requerida
                          ? " (requerida)"
                          : " (sin seña)"
                    }`}
                {prestacion.activa ? "" : " (inactiva)"}
                {puedeEditarCatalogo && (
                  <>
                    <button type="button" onClick={() => {
                      setPrestacionEditando(prestacion.id);
                      setNombrePrestacion(prestacion.nombre);
                      setDuracion(String(prestacion.duracion_min));
                      setPrecio(prestacion.precio_ref === null ? "" : String(prestacion.precio_ref));
                      setPrestacionActiva(prestacion.activa);
                      setSeniaRequerida(
                        prestacion.senia_requerida === null
                          ? "global"
                          : prestacion.senia_requerida
                            ? "si"
                            : "no",
                      );
                      setSeniaMonto(
                        prestacion.senia_monto_cents === null
                          ? ""
                          : String(prestacion.senia_monto_cents),
                      );
                    }}>Editar</button>
                    <button type="button" disabled={guardando} onClick={() => {
                      void ejecutar(async () => {
                        await eliminarPrestacion(request, prestacion.id);
                        await recargar();
                      }, "Prestación eliminada.");
                    }}>Eliminar</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        {puedeEditarCatalogo && (
          <form onSubmit={(event) => void guardarPrestacionFormulario(event)}>
            <label>
              Nombre de la prestación
              <input
                value={nombrePrestacion}
                onChange={(event) => setNombrePrestacion(event.target.value)}
                required
              />
            </label>
            <label>
              Duración (minutos)
              <input
                type="number"
                min={5}
                max={240}
                step={1}
                value={duracion}
                onChange={(event) => setDuracion(event.target.value)}
                required
              />
            </label>
            <label>
              Precio de referencia (centavos)
              <input
                type="number"
                min={0}
                step={1}
                value={precio}
                onChange={(event) => setPrecio(event.target.value)}
              />
            </label>
            <label>
              Activa
              <input
                name="activa"
                type="checkbox"
                checked={prestacionActiva}
                onChange={(event) => setPrestacionActiva(event.target.checked)}
              />
            </label>
            <label>
              Seña del turno
              <select
                value={seniaRequerida}
                onChange={(event) =>
                  setSeniaRequerida(event.target.value as "global" | "si" | "no")
                }
              >
                <option value="global">Según configuración global</option>
                <option value="si">Requerida para esta prestación</option>
                <option value="no">No requiere seña</option>
              </select>
            </label>
            <label>
              Monto de la seña (centavos)
              <input
                type="number"
                min={0}
                step={1}
                value={seniaMonto}
                onChange={(event) => setSeniaMonto(event.target.value)}
                disabled={seniaRequerida === "no"}
              />
            </label>
            <button type="submit" disabled={guardando}>
              {prestacionEditando === null ? "Guardar prestación" : "Actualizar prestación"}
            </button>
            {prestacionEditando !== null && (
              <button type="button" onClick={() => {
                setPrestacionEditando(null);
                setNombrePrestacion("");
                setDuracion("30");
                setPrecio("");
                setPrestacionActiva(true);
                setSeniaRequerida("global");
                setSeniaMonto("");
              }}>Cancelar edición</button>
            )}
          </form>
        )}
      </section>

      <section aria-labelledby="titulo-horarios">
        <h3 id="titulo-horarios">Horarios semanales</h3>
        <label>
          Profesional
          <select
            value={profesionalHorario}
            onChange={(event) => setProfesionalHorario(event.target.value)}
          >
            <option value="">Seleccionar profesional</option>
            {profesionales.map((profesional) => (
              <option key={profesional.id} value={profesional.id}>{profesional.nombre}</option>
            ))}
          </select>
        </label>
        {zonaHoraria !== "" && <p>Zona horaria: {zonaHoraria}</p>}
        {profesionalHorario !== "" && (
          <>
            <ul>
              {horarios.map((horario, index) => (
                <li key={`${horario.dia_semana}-${horario.inicio}-${index}`}>
                  {DIAS_SEMANA[horario.dia_semana]} {horario.inicio}–{horario.fin}
                  {puedeEditarCatalogo && (
                    <button type="button" onClick={() =>
                      setHorarios((actuales) => actuales.filter((_, itemIndex) => itemIndex !== index))
                    }>Quitar</button>
                  )}
                </li>
              ))}
            </ul>
            {puedeEditarCatalogo && (
              <>
                <form onSubmit={(event) => void agregarHorario(event)}>
                  <label>
                    Día
                    <select value={diaHorario} onChange={(event) => setDiaHorario(event.target.value)}>
                      {DIAS_SEMANA.map((dia, index) => (
                        <option key={dia} value={index}>{dia}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Inicio
                    <input type="time" value={inicioHorario} onChange={(event) => setInicioHorario(event.target.value)} />
                  </label>
                  <label>
                    Fin
                    <input type="time" value={finHorario} onChange={(event) => setFinHorario(event.target.value)} />
                  </label>
                  <button type="submit">Agregar horario</button>
                </form>
                <button type="button" disabled={guardando} onClick={() => {
                  void ejecutar(async () => {
                    await guardarHorarios(request, profesionalHorario, horarios);
                    const actualizados = await obtenerHorarios(request, profesionalHorario);
                    setHorarios(actualizados.horarios.map(({ dia_semana, inicio, fin }) => ({
                      dia_semana,
                      inicio: inicio.slice(0, 5),
                      fin: fin.slice(0, 5),
                    })));
                  }, "Horarios guardados.");
                }}>Guardar horarios</button>
              </>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="titulo-bloqueos">
        <h3 id="titulo-bloqueos">Bloqueos</h3>
        {bloqueos.length === 0 ? (
          <p>No hay bloqueos registrados.</p>
        ) : (
          <ul>
            {bloqueos.map((bloqueo) => (
              <li key={bloqueo.id}>
                {profesionales.find((profesional) => profesional.id === bloqueo.profesional_id)?.nombre ?? "Profesional"}
                {" — "}{bloqueo.inicio} a {bloqueo.fin}
                {bloqueo.motivo ? ` — ${bloqueo.motivo}` : ""}
                {puedeEditarCatalogo && (
                  <>
                    <button type="button" onClick={() => {
                      setBloqueoEditando(bloqueo.id);
                      setProfesionalBloqueo(bloqueo.profesional_id);
                      setInicioBloqueo(bloqueo.inicio);
                      setFinBloqueo(bloqueo.fin);
                      setMotivoBloqueo(bloqueo.motivo ?? "");
                    }}>Editar</button>
                    <button type="button" disabled={guardando} onClick={() => {
                      void ejecutar(async () => {
                        await eliminarBloqueo(request, bloqueo.id);
                        setBloqueos(await listarBloqueos(request));
                      }, "Bloqueo eliminado.");
                    }}>Eliminar</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        {puedeEditarCatalogo && (
          <form onSubmit={(event) => void guardarBloqueo(event)}>
            <label>
              Profesional del bloqueo
              <select value={profesionalBloqueo} onChange={(event) => setProfesionalBloqueo(event.target.value)} required>
                <option value="">Seleccionar profesional</option>
                {profesionales.map((profesional) => (
                  <option key={profesional.id} value={profesional.id}>{profesional.nombre}</option>
                ))}
              </select>
            </label>
            <label>
              Inicio (ISO 8601 con offset)
              <input
                value={inicioBloqueo}
                onChange={(event) => setInicioBloqueo(event.target.value)}
                placeholder="2026-11-02T10:00:00-03:00"
                required
              />
            </label>
            <label>
              Fin (ISO 8601 con offset)
              <input
                value={finBloqueo}
                onChange={(event) => setFinBloqueo(event.target.value)}
                placeholder="2026-11-02T11:00:00-03:00"
                required
              />
            </label>
            <label>
              Motivo (opcional)
              <input value={motivoBloqueo} onChange={(event) => setMotivoBloqueo(event.target.value)} maxLength={500} />
            </label>
            <button type="submit" disabled={guardando}>
              {bloqueoEditando === null ? "Crear bloqueo" : "Actualizar bloqueo"}
            </button>
            {bloqueoEditando !== null && (
              <button type="button" onClick={() => {
                setBloqueoEditando(null);
                setInicioBloqueo("");
                setFinBloqueo("");
                setMotivoBloqueo("");
              }}>Cancelar edición</button>
            )}
          </form>
        )}
      </section>

      {esDueno && (
        <section aria-labelledby="titulo-reglas">
          <h3 id="titulo-reglas">Configuración global de agenda</h3>
          <form onSubmit={(event) => void guardarConfiguracionFormulario(event)}>
            <label>
              Antelación mínima para cancelar (horas)
              <input
                name="antelacion_cancel_hs"
                type="number"
                min={0}
                step={1}
                value={configuracion.antelacion_cancel_hs}
                onChange={(event) => setConfiguracion((actual) => ({
                  ...actual,
                  antelacion_cancel_hs: Number(event.target.value),
                }))}
                required
              />
            </label>
            <label>
              Antelación mínima para reservar (horas)
              <input
                name="antelacion_reserva_hs"
                type="number"
                min={0}
                step={1}
                value={configuracion.antelacion_reserva_hs}
                onChange={(event) => setConfiguracion((actual) => ({
                  ...actual,
                  antelacion_reserva_hs: Number(event.target.value),
                }))}
                required
              />
            </label>
            <label>
              Recordatorio T-48 h
              <input
                name="recordatorio_t_48h"
                type="checkbox"
                checked={configuracion.recordatorio_t_48h}
                onChange={(event) => setConfiguracion((actual) => ({
                  ...actual,
                  recordatorio_t_48h: event.target.checked,
                }))}
              />
            </label>
            <label>
              Recordatorio T-24 h
              <input
                name="recordatorio_t_24h"
                type="checkbox"
                checked={configuracion.recordatorio_t_24h}
                onChange={(event) => setConfiguracion((actual) => ({
                  ...actual,
                  recordatorio_t_24h: event.target.checked,
                }))}
              />
            </label>
            <label>
              Política de devolución de seña
              <select
                value={configuracion.politica_devolucion_senia}
                onChange={(event) =>
                  setConfiguracion((actual) => ({
                    ...actual,
                    politica_devolucion_senia: event.target
                      .value as ConfiguracionAgenda["politica_devolucion_senia"],
                  }))
                }
              >
                {POLITICAS_DEVOLUCION.map((politica) => (
                  <option key={politica.valor} value={politica.valor}>
                    {politica.etiqueta}
                  </option>
                ))}
              </select>
            </label>
            <p>La antelación de cancelación es global y no puede configurarse por prestación.</p>
            <button type="submit" disabled={guardando}>Guardar configuración</button>
          </form>
        </section>
      )}
    </section>
  );
}
