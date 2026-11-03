import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../../shared/api/client";
import { useAuth } from "../auth/auth";
import { listarPacientes } from "../pacientes/api";
import type { Paciente } from "../pacientes/api";
import {
  consultarAgenda,
  consultarDisponibilidad,
  crearTurno,
  ejecutarAccionTurno,
  reprogramarTurno,
} from "./api";
import type { TurnoAgenda } from "./api";
import {
  listarPrestaciones,
  listarProfesionales,
  obtenerHorarios,
} from "./catalogoApi";
import type { Prestacion, Profesional } from "./catalogoApi";
import { CancelarTurnoButton } from "./CancelarTurno";
import "./AgendaPage.css";

type VistaAgenda = "dia" | "semana";

function fechaLocal(date = new Date()): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function mostrarError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : "No se pudo completar la operación. Probá de nuevo.";
}

function partesEnZona(iso: string, zona: string): Record<string, string> {
  return Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: zona,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(iso))
      .filter((parte) => parte.type !== "literal")
      .map((parte) => [parte.type, parte.value]),
  );
}

function aFechaHoraLocal(iso: string, zona: string): string {
  const partes = partesEnZona(iso, zona);
  return `${partes["year"]}-${partes["month"]}-${partes["day"]}T${partes["hour"]}:${partes["minute"]}`;
}

function aIsoEnZona(valor: string, zona: string): string {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(valor);
  if (coincidencia === null) throw new Error("Ingresá una fecha y hora válidas.");
  const [, anio, mes, dia, hora, minuto] = coincidencia;
  const paredUtc = Date.UTC(
    Number(anio),
    Number(mes) - 1,
    Number(dia),
    Number(hora),
    Number(minuto),
  );
  const offsetEn = (instante: number): number => {
    const partes = partesEnZona(new Date(instante).toISOString(), zona);
    const paredMostrada = Date.UTC(
      Number(partes["year"]),
      Number(partes["month"]) - 1,
      Number(partes["day"]),
      Number(partes["hour"]),
      Number(partes["minute"]),
    );
    return paredMostrada - instante;
  };
  const instante = paredUtc - offsetEn(paredUtc);
  if (aFechaHoraLocal(new Date(instante).toISOString(), zona) !== valor) {
    throw new Error("Ese horario no existe en la zona horaria del consultorio.");
  }
  return new Date(instante).toISOString();
}

function sumarMinutosLocales(valor: string, minutos: number): string {
  const base = new Date(`${valor}:00Z`);
  base.setUTCMinutes(base.getUTCMinutes() + minutos);
  return `${base.toISOString().slice(0, 16)}`;
}

function fechaLarga(fecha: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "full",
    timeZone: "UTC",
  }).format(new Date(`${fecha}T12:00:00Z`));
}

function horaEnZona(iso: string, zona: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: zona,
  }).format(new Date(iso));
}

interface HorariosDisponiblesProps {
  cargando: boolean;
  horarios: string[];
  inicioSeleccionado: string;
  zona: string;
  onSeleccionar: (horario: string) => void;
}

function HorariosDisponibles({
  cargando,
  horarios,
  inicioSeleccionado,
  zona,
  onSeleccionar,
}: HorariosDisponiblesProps): JSX.Element {
  return (
    <div className="agenda-horarios-disponibles" aria-live="polite">
      <h4>Horarios disponibles sugeridos</h4>
      {cargando ? (
        <p>Buscando horarios…</p>
      ) : horarios.length > 0 ? (
        horarios.map((horario) => (
          <button
            type="button"
            key={horario}
            aria-pressed={aFechaHoraLocal(horario, zona) === inicioSeleccionado}
            onClick={() => onSeleccionar(horario)}
          >
            {horaEnZona(horario, zona)}
          </button>
        ))
      ) : (
        <p>No hay horarios libres para esa prestación en esta fecha.</p>
      )}
    </div>
  );
}

function etiquetaEstado(estado: string): string {
  const etiquetas: Record<string, string> = {
    confirmado: "Confirmado",
    pendiente_confirmacion: "Pendiente de confirmación",
    presente: "Presente",
    ausente: "Ausente",
    cancelado: "Cancelado",
    reprogramado: "Reprogramado",
  };
  return etiquetas[estado] ?? estado;
}

export function AgendaPage(): JSX.Element {
  const { request, user } = useAuth();
  const [fecha, setFecha] = useState(fechaLocal);
  const [vista, setVista] = useState<VistaAgenda>("dia");
  const [profesionalId, setProfesionalId] = useState("");
  const [profesionales, setProfesionales] = useState<Profesional[]>([]);
  const [prestaciones, setPrestaciones] = useState<Prestacion[]>([]);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [zona, setZona] = useState("UTC");
  const [turnos, setTurnos] = useState<TurnoAgenda[]>([]);
  const [cargandoCatalogos, setCargandoCatalogos] = useState(true);
  const [cargandoAgenda, setCargandoAgenda] = useState(true);
  const [cargandoDisponibilidad, setCargandoDisponibilidad] = useState(false);
  const [horariosDisponibles, setHorariosDisponibles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [mostrarAlta, setMostrarAlta] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [pacienteId, setPacienteId] = useState("");
  const [nuevoProfesionalId, setNuevoProfesionalId] = useState("");
  const [prestacionId, setPrestacionId] = useState("");
  const [sobreturno, setSobreturno] = useState(false);
  const [sobreturnoMotivo, setSobreturnoMotivo] = useState("");
  const [inicioLocal, setInicioLocal] = useState(`${fecha}T09:00`);
  const [alternativas, setAlternativas] = useState<string[]>([]);
  const [reprogramandoId, setReprogramandoId] = useState<string | null>(null);
  const [inicioReprogramacion, setInicioReprogramacion] = useState("");
  const [profesionalReprogramacionId, setProfesionalReprogramacionId] = useState("");
  const [prestacionReprogramacionId, setPrestacionReprogramacionId] = useState("");

  const puedeGestionar =
    user?.roles.some((rol) => rol === "recepcion" || rol === "dueno") ?? false;
  const pacientesPorId = useMemo(
    () => new Map(pacientes.map((paciente) => [paciente.id, paciente])),
    [pacientes],
  );
  const profesionalesPorId = useMemo(
    () => new Map(profesionales.map((profesional) => [profesional.id, profesional])),
    [profesionales],
  );
  const prestacionesPorId = useMemo(
    () => new Map(prestaciones.map((prestacion) => [prestacion.id, prestacion])),
    [prestaciones],
  );

  useEffect(() => {
    let vigente = true;
    setCargandoCatalogos(true);
    setError(null);
    void Promise.all([
      listarProfesionales(request),
      listarPrestaciones(request),
      listarPacientes(request, ""),
    ])
      .then(async ([profesionalesCargados, prestacionesCargadas, pacientesCargados]) => {
        let zonaCargada = "UTC";
        const profesionalInicial = profesionalesCargados[0];
        if (profesionalInicial !== undefined) {
          zonaCargada = (await obtenerHorarios(request, profesionalInicial.id)).zona_horaria;
        }
        if (!vigente) return;
        setProfesionales(profesionalesCargados.filter((item) => item.activo));
        setPrestaciones(prestacionesCargadas.filter((item) => item.activa));
        setPacientes(pacientesCargados);
        setZona(zonaCargada);
      })
      .catch((loadError: unknown) => {
        if (vigente) setError(mostrarError(loadError));
      })
      .finally(() => {
        if (vigente) setCargandoCatalogos(false);
      });
    return () => {
      vigente = false;
    };
  }, [request]);

  useEffect(() => {
    let vigente = true;
    setCargandoAgenda(true);
    setError(null);
    void consultarAgenda(request, vista, fecha, profesionalId || undefined)
      .then((items) => {
        if (vigente) setTurnos(items);
      })
      .catch((loadError: unknown) => {
        if (vigente) setError(mostrarError(loadError));
      })
      .finally(() => {
        if (vigente) setCargandoAgenda(false);
      });
    return () => {
      vigente = false;
    };
  }, [fecha, profesionalId, request, vista]);

  async function refrescarAgenda(): Promise<void> {
    setCargandoAgenda(true);
    try {
      setTurnos(await consultarAgenda(request, vista, fecha, profesionalId || undefined));
    } catch (loadError: unknown) {
      setError(mostrarError(loadError));
    } finally {
      setCargandoAgenda(false);
    }
  }

  function moverPeriodo(dias: number): void {
    const actual = new Date(`${fecha}T12:00:00Z`);
    actual.setUTCDate(actual.getUTCDate() + dias);
    setFecha(actual.toISOString().slice(0, 10));
  }

  function abrirAlta(): void {
    setError(null);
    setMensaje(null);
    setAlternativas([]);
    setPacienteId("");
    setNuevoProfesionalId(profesionalId || profesionales[0]?.id || "");
    setPrestacionId("");
    setSobreturno(false);
    setSobreturnoMotivo("");
    setInicioLocal(`${fecha}T09:00`);
    setMostrarAlta(true);
  }

  async function crear(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    const profesional = profesionalesPorId.get(nuevoProfesionalId);
    if (profesional === undefined) {
      setError("Elegí un profesional activo.");
      return;
    }
    const prestacion = prestacionesPorId.get(prestacionId);
    const duracion = prestacion?.duracion_min ?? 30;
    setGuardando(true);
    setError(null);
    setMensaje(null);
    setAlternativas([]);
    try {
      const inicio = aIsoEnZona(inicioLocal, zona);
      const fin = aIsoEnZona(sumarMinutosLocales(inicioLocal, duracion), zona);
      await crearTurno(
        request,
        {
          paciente_id: pacienteId,
          profesional_id: profesional.id,
          prestacion_id: prestacion?.id ?? null,
          inicio,
          fin,
          sobreturno,
          sobreturno_motivo: sobreturno ? sobreturnoMotivo.trim() : null,
        },
        crypto.randomUUID(),
      );
      setMostrarAlta(false);
      setMensaje("Turno creado.");
      await refrescarAgenda();
    } catch (saveError: unknown) {
      if (saveError instanceof ApiError) setAlternativas(saveError.alternativas ?? []);
      setError(mostrarError(saveError));
    } finally {
      setGuardando(false);
    }
  }

  async function ejecutarAccion(
    turnoId: string,
    accion: "confirmar" | "presente" | "ausente",
  ): Promise<void> {
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      await ejecutarAccionTurno(request, turnoId, accion);
      setMensaje(
        accion === "presente"
          ? "Asistencia registrada."
          : accion === "ausente"
            ? "Ausencia registrada."
            : "Turno confirmado.",
      );
      await refrescarAgenda();
    } catch (actionError: unknown) {
      setError(mostrarError(actionError));
    } finally {
      setGuardando(false);
    }
  }

  async function guardarReprogramacion(
    ev: FormEvent<HTMLFormElement>,
    turno: TurnoAgenda,
  ): Promise<void> {
    ev.preventDefault();
    const datos = new FormData(ev.currentTarget);
    const fechaHora = String(datos.get("reprogramar-inicio") ?? "");
    const profesionalDestino = String(datos.get("reprogramar-profesional") ?? "");
    const prestacionDestino = String(datos.get("reprogramar-prestacion") ?? "");
    const duracion = prestacionesPorId.get(prestacionDestino)?.duracion_min ?? 30;
    setGuardando(true);
    setError(null);
    setAlternativas([]);
    try {
      const inicio = aIsoEnZona(fechaHora, zona);
      const fin = aIsoEnZona(sumarMinutosLocales(fechaHora, duracion), zona);
      await reprogramarTurno(request, turno.id, {
        profesional_id: profesionalDestino,
        prestacion_id: prestacionDestino || null,
        inicio,
        fin,
      });
      setReprogramandoId(null);
      setMensaje("Turno reprogramado.");
      await refrescarAgenda();
    } catch (saveError: unknown) {
      if (saveError instanceof ApiError) setAlternativas(saveError.alternativas ?? []);
      setError(mostrarError(saveError));
    } finally {
      setGuardando(false);
    }
  }

  function aplicarAlternativa(iso: string): void {
    const valorLocal = aFechaHoraLocal(iso, zona);
    if (reprogramandoId !== null) setInicioReprogramacion(valorLocal);
    else setInicioLocal(valorLocal);
    setError(null);
    setAlternativas([]);
  }

  function iniciarReprogramacion(turno: TurnoAgenda): void {
    setMostrarAlta(false);
    setInicioReprogramacion(aFechaHoraLocal(turno.inicio, zona));
    setProfesionalReprogramacionId(turno.profesional_id);
    setPrestacionReprogramacionId(turno.prestacion_id ?? "");
    setReprogramandoId(turno.id);
  }

  const desplazamiento = vista === "dia" ? 1 : 7;
  const formularioAbierto = mostrarAlta || reprogramandoId !== null;
  const fechaInicioDisponibilidad =
    reprogramandoId !== null ? inicioReprogramacion : inicioLocal;
  const profesionalDisponibilidadId =
    reprogramandoId !== null ? profesionalReprogramacionId : nuevoProfesionalId;
  const prestacionDisponibilidadId =
    reprogramandoId !== null ? prestacionReprogramacionId : prestacionId;
  const fechaDisponibilidad = fechaInicioDisponibilidad.slice(0, 10);

  useEffect(() => {
    if (
      !formularioAbierto ||
      profesionalDisponibilidadId === "" ||
      prestacionDisponibilidadId === ""
    ) {
      setHorariosDisponibles([]);
      setCargandoDisponibilidad(false);
      return;
    }
    let vigente = true;
    setCargandoDisponibilidad(true);
    const siguienteDia = new Date(`${fechaDisponibilidad}T12:00:00Z`);
    siguienteDia.setUTCDate(siguienteDia.getUTCDate() + 1);
    let desde: string;
    let hasta: string;
    try {
      desde = aIsoEnZona(`${fechaDisponibilidad}T00:00`, zona);
      hasta = aIsoEnZona(
        `${siguienteDia.toISOString().slice(0, 10)}T00:00`,
        zona,
      );
    } catch (dateError: unknown) {
      setError(mostrarError(dateError));
      setCargandoDisponibilidad(false);
      return;
    }
    void consultarDisponibilidad(
      request,
      profesionalDisponibilidadId,
      prestacionDisponibilidadId,
      desde,
      hasta,
    )
      .then((horarios) => {
        if (vigente) setHorariosDisponibles(horarios);
      })
      .catch((availabilityError: unknown) => {
        if (vigente) setError(mostrarError(availabilityError));
      })
      .finally(() => {
        if (vigente) setCargandoDisponibilidad(false);
      });
    return () => {
      vigente = false;
    };
  }, [
    fechaDisponibilidad,
    formularioAbierto,
    profesionalDisponibilidadId,
    prestacionDisponibilidadId,
    request,
    zona,
  ]);

  return (
    <section className="agenda-page" aria-labelledby="agenda-titulo">
      <header className="agenda-header">
        <div>
          <h2 id="agenda-titulo">Agenda</h2>
          <p>Organizá los turnos del consultorio.</p>
        </div>
        {puedeGestionar && (
          <button type="button" className="agenda-primary" onClick={abrirAlta}>
            Nuevo turno
          </button>
        )}
      </header>

      <div className="agenda-toolbar" aria-label="Controles de agenda">
        <div className="agenda-periodo">
          <button
            type="button"
            aria-label="Período anterior"
            onClick={() => moverPeriodo(-desplazamiento)}
          >
            Anterior
          </button>
          <label>
            <span className="sr-only">Fecha de agenda</span>
            <input
              type="date"
              value={fecha}
              onChange={(event) => setFecha(event.currentTarget.value)}
            />
          </label>
          <button
            type="button"
            aria-label="Período siguiente"
            onClick={() => moverPeriodo(desplazamiento)}
          >
            Siguiente
          </button>
          <button type="button" onClick={() => setFecha(fechaLocal())}>
            Hoy
          </button>
        </div>

        <div className="agenda-filtros">
          <div className="agenda-vistas" role="group" aria-label="Vista de agenda">
            <button
              type="button"
              aria-pressed={vista === "dia"}
              onClick={() => setVista("dia")}
            >
              Día
            </button>
            <button
              type="button"
              aria-pressed={vista === "semana"}
              onClick={() => setVista("semana")}
            >
              Semana
            </button>
          </div>
          <label>
            Profesional
            <select
              value={profesionalId}
              onChange={(event) => setProfesionalId(event.currentTarget.value)}
            >
              <option value="">Todos</option>
              {profesionales.map((profesional) => (
                <option key={profesional.id} value={profesional.id}>
                  {profesional.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <p className="agenda-fecha" aria-live="polite">
        {fechaLarga(fecha)} <span>· {zona}</span>
      </p>

      {error !== null && (
        <div className="agenda-alerta" role="alert">
          <p>{error}</p>
          {alternativas.length > 0 && (
            <div className="agenda-alternativas">
              <p>Probá alguno de estos horarios disponibles:</p>
              {alternativas.map((alternativa) => (
                <button
                  type="button"
                  key={alternativa}
                  onClick={() => aplicarAlternativa(alternativa)}
                >
                  {new Intl.DateTimeFormat("es-AR", {
                    dateStyle: "short",
                    timeStyle: "short",
                    hourCycle: "h23",
                    timeZone: zona,
                  }).format(new Date(alternativa))}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {mensaje !== null && <p className="agenda-mensaje" role="status">{mensaje}</p>}

      {mostrarAlta && puedeGestionar && (
        <form className="agenda-formulario" onSubmit={(event) => void crear(event)}>
          <div className="agenda-formulario-header">
            <h3>Nuevo turno</h3>
            <button type="button" onClick={() => setMostrarAlta(false)}>
              Cerrar
            </button>
          </div>
          <div className="agenda-form-grid">
            <label>
              Paciente
              <select
                required
                value={pacienteId}
                onChange={(event) => setPacienteId(event.currentTarget.value)}
              >
                <option value="">Seleccioná un paciente</option>
                {pacientes.map((paciente) => (
                  <option key={paciente.id} value={paciente.id}>
                    {paciente.apellido}, {paciente.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Profesional
              <select
                required
                value={nuevoProfesionalId}
                onChange={(event) => setNuevoProfesionalId(event.currentTarget.value)}
              >
                <option value="">Seleccioná un profesional</option>
                {profesionales.map((profesional) => (
                  <option key={profesional.id} value={profesional.id}>
                    {profesional.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Prestación
              <select
                value={prestacionId}
                onChange={(event) => setPrestacionId(event.currentTarget.value)}
              >
                <option value="">Sin prestación (30 minutos)</option>
                {prestaciones.map((prestacion) => (
                  <option key={prestacion.id} value={prestacion.id}>
                    {prestacion.nombre} · {prestacion.duracion_min} min
                  </option>
                ))}
              </select>
            </label>
            <label>
              Inicio
              <input
                type="datetime-local"
                required
                value={inicioLocal}
                onChange={(event) => setInicioLocal(event.currentTarget.value)}
              />
            </label>
          </div>
          <label className="agenda-checkbox">
            <input
              type="checkbox"
              checked={sobreturno}
              onChange={(event) => setSobreturno(event.currentTarget.checked)}
            />
            Registrar como sobreturno
          </label>
          {sobreturno && (
            <label>
              Motivo del sobreturno
              <textarea
                required
                maxLength={500}
                value={sobreturnoMotivo}
                onChange={(event) => setSobreturnoMotivo(event.currentTarget.value)}
              />
            </label>
          )}
          <p className="agenda-ayuda">
            La duración se calcula según la prestación. La hora se interpreta en {zona}.
          </p>
          {prestacionId !== "" && (
            <HorariosDisponibles
              cargando={cargandoDisponibilidad}
              horarios={horariosDisponibles}
              inicioSeleccionado={inicioLocal}
              zona={zona}
              onSeleccionar={(horario) =>
                setInicioLocal(aFechaHoraLocal(horario, zona))
              }
            />
          )}
          <button type="submit" className="agenda-primary" disabled={guardando}>
            {guardando ? "Guardando…" : "Guardar turno"}
          </button>
        </form>
      )}

      {cargandoAgenda || cargandoCatalogos ? (
        <div className="agenda-cargando" role="status" aria-live="polite">
          Cargando agenda…
        </div>
      ) : turnos.length === 0 ? (
        <div className="agenda-vacia">
          <h3>No hay turnos en este período</h3>
          <p>Probá otra fecha o cambiá el filtro de profesional.</p>
          {puedeGestionar && (
            <button type="button" onClick={abrirAlta}>
              Crear un turno
            </button>
          )}
        </div>
      ) : (
        <ol className="agenda-lista" aria-label={`Turnos de ${fechaLarga(fecha)}`}>
          {turnos.map((turno) => {
            const paciente = pacientesPorId.get(turno.paciente_id);
            const profesional = profesionalesPorId.get(turno.profesional_id);
            const prestacion = turno.prestacion_id
              ? prestacionesPorId.get(turno.prestacion_id)
              : undefined;
            const puedeCancelar =
              puedeGestionar ||
              (user?.roles.includes("odontologo") === true &&
                turno.profesional_usuario_id === user.sub);
            return (
              <li className="agenda-fila" key={turno.id}>
                <time className="agenda-hora" dateTime={turno.inicio}>
                  {horaEnZona(turno.inicio, zona)}
                  <span>{horaEnZona(turno.fin, zona)}</span>
                </time>
                <div className="agenda-detalle">
                  <h3>
                    {paciente === undefined
                      ? "Paciente no disponible"
                      : `${paciente.apellido}, ${paciente.nombre}`}
                  </h3>
                  <p>
                    {profesional?.nombre ?? "Profesional no disponible"}
                    {prestacion !== undefined ? ` · ${prestacion.nombre}` : ""}
                  </p>
                  {turno.sobreturno && (
                    <p className="agenda-sobreturno">
                      Sobreturno · {turno.sobreturno_motivo}
                    </p>
                  )}
                  {turno.motivo !== null && (
                    <p className="agenda-motivo">{turno.motivo}</p>
                  )}
                </div>
                <span className={`agenda-estado agenda-estado-${turno.estado}`}>
                  {etiquetaEstado(turno.estado)}
                </span>
                {puedeCancelar && (
                  <div className="agenda-acciones">
                    {puedeGestionar && turno.estado === "pendiente_confirmacion" && (
                      <button
                        type="button"
                        disabled={guardando}
                        onClick={() => void ejecutarAccion(turno.id, "confirmar")}
                      >
                        Confirmar
                      </button>
                    )}
                    {puedeGestionar && turno.estado === "confirmado" && (
                      <>
                        <button
                          type="button"
                          disabled={guardando}
                          onClick={() => void ejecutarAccion(turno.id, "presente")}
                        >
                          Presente
                        </button>
                        <button
                          type="button"
                          disabled={guardando}
                          onClick={() =>
                            reprogramandoId === turno.id
                              ? setReprogramandoId(null)
                              : iniciarReprogramacion(turno)
                          }
                        >
                          Reprogramar
                        </button>
                        <button
                          type="button"
                          disabled={guardando}
                          onClick={() => void ejecutarAccion(turno.id, "ausente")}
                        >
                          Ausente
                        </button>
                      </>
                    )}
                    {puedeCancelar &&
                      ["confirmado", "pendiente_confirmacion"].includes(turno.estado) && (
                        <CancelarTurnoButton
                          turnoId={turno.id}
                          onReprogramar={
                            puedeGestionar ? () => iniciarReprogramacion(turno) : undefined
                          }
                          onCancelado={() => {
                            setMensaje("Turno cancelado.");
                            void refrescarAgenda();
                          }}
                        />
                      )}
                  </div>
                )}
                {reprogramandoId === turno.id && (
                  <form
                    className="agenda-reprogramar"
                    onSubmit={(event) => void guardarReprogramacion(event, turno)}
                  >
                    <label>
                      Nuevo inicio
                      <input
                        name="reprogramar-inicio"
                        type="datetime-local"
                        required
                        value={inicioReprogramacion}
                        onChange={(event) =>
                          setInicioReprogramacion(event.currentTarget.value)
                        }
                      />
                    </label>
                    <label>
                      Profesional
                      <select
                        name="reprogramar-profesional"
                        value={profesionalReprogramacionId}
                        onChange={(event) =>
                          setProfesionalReprogramacionId(event.currentTarget.value)
                        }
                        required
                      >
                        {profesionales.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.nombre}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Prestación
                      <select
                        name="reprogramar-prestacion"
                        value={prestacionReprogramacionId}
                        onChange={(event) =>
                          setPrestacionReprogramacionId(event.currentTarget.value)
                        }
                      >
                        <option value="">Sin prestación (30 minutos)</option>
                        {prestaciones.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.nombre} · {item.duracion_min} min
                          </option>
                        ))}
                      </select>
                    </label>
                    {prestacionReprogramacionId !== "" && (
                      <HorariosDisponibles
                        cargando={cargandoDisponibilidad}
                        horarios={horariosDisponibles}
                        inicioSeleccionado={inicioReprogramacion}
                        zona={zona}
                        onSeleccionar={(horario) =>
                          setInicioReprogramacion(aFechaHoraLocal(horario, zona))
                        }
                      />
                    )}
                    <button type="submit" className="agenda-primary" disabled={guardando}>
                      {guardando ? "Guardando…" : "Guardar reprogramación"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setReprogramandoId(null)}
                    >
                      Volver
                    </button>
                  </form>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
