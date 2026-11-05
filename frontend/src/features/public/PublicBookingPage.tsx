import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  cancelPublicBooking,
  confirmPublicBooking,
  createPublicBooking,
  getPublicAvailability,
  reschedulePublicBooking,
  PublicAvailability,
  PublicBookingPayload,
} from "./api";
import { ApiError } from "../../shared/api/client";

export function PublicBookingPage(): JSX.Element {
  const { slug = "" } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const actionToken = searchParams.get("token") ?? "";
  const action = searchParams.get("accion") ?? "";
  const [data, setData] = useState<PublicAvailability | null>(null);
  const [professionalId, setProfessionalId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [slot, setSlot] = useState("");
  const [form, setForm] = useState({ nombre: "", apellido: "", telefono: "", email: "", whatsapp: false });
  const [message, setMessage] = useState("Elegí un profesional y una prestación.");
  const [loading, setLoading] = useState(false);
  const [actionResult, setActionResult] = useState("");

  const range = useMemo(() => {
    const now = new Date();
    const until = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
    return { desde: now.toISOString(), hasta: until.toISOString() };
  }, []);

  useEffect(() => {
    if (!slug) return;
    let active = true;
    setLoading(true);
    void getPublicAvailability(slug, professionalId, serviceId, range.desde, range.hasta)
      .then((response) => {
        if (active) {
          setData(response);
          setMessage(response.slots.length ? "Elegí un horario." : "No hay horarios disponibles.");
        }
      })
      .catch(() => {
        if (active) setMessage("No pudimos cargar la disponibilidad. Probá de nuevo.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [range.desde, range.hasta, professionalId, serviceId, slug]);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!slot) {
      setMessage("Elegí un horario antes de continuar.");
      return;
    }
    const payload: PublicBookingPayload = {
      tenant_slug: slug,
      profesional_id: professionalId,
      prestacion_id: serviceId,
      inicio: slot,
      nombre: form.nombre,
      apellido: form.apellido,
      telefono: form.telefono || undefined,
      email: form.email || undefined,
      whatsapp_opt_in: form.whatsapp,
    };
    setLoading(true);
    try {
      const result = await createPublicBooking(payload, crypto.randomUUID());
      setMessage(`Reserva creada. Estado: ${result.estado}. Guardá este enlace para gestionarla.`);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "No pudimos crear la reserva. El horario puede haberse ocupado.");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(kind: "confirmar" | "cancelar"): Promise<void> {
    if (!actionToken) return;
    setLoading(true);
    try {
      const result = kind === "confirmar"
        ? await confirmPublicBooking(actionToken, slug)
        : await cancelPublicBooking(actionToken, slug);
      setActionResult(`Turno ${result.estado}.`);
    } catch (error) {
      setActionResult(error instanceof ApiError ? error.message : "No pudimos completar la acción.");
    } finally {
      setLoading(false);
    }
  }

  async function reschedule(): Promise<void> {
    if (!actionToken || !slot) return;
    setLoading(true);
    try {
      const result = await reschedulePublicBooking(actionToken, {
        tenant_slug: slug,
        profesional_id: professionalId,
        prestacion_id: serviceId,
        inicio: slot,
      });
      setActionResult(`Reprogramación solicitada. Estado: ${result.estado}.`);
    } catch (error) {
      const detail = error instanceof ApiError && error.alternativas?.length
        ? ` Opciones: ${error.alternativas.map((item) => new Date(item).toLocaleString("es-AR")).join(", ")}`
        : "";
      setActionResult(`${error instanceof ApiError ? error.message : "No pudimos reprogramar el turno."}${detail}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main aria-labelledby="public-booking-title">
      <h1 id="public-booking-title">Reservá tu turno</h1>
      <p>{message}</p>
      {actionToken && (
        <section aria-labelledby="public-action-title">
          <h2 id="public-action-title">Gestioná tu turno</h2>
          <p role="status">{actionResult}</p>
          {(action === "confirmar" || !action) && (
            <button type="button" disabled={loading} onClick={() => void runAction("confirmar")}>Confirmar turno</button>
          )}
          {(action === "cancelar" || !action) && (
            <button type="button" disabled={loading} onClick={() => void runAction("cancelar")}>Cancelar turno</button>
          )}
        </section>
      )}
      <label>
        Profesional
        <select value={professionalId} onChange={(event) => setProfessionalId(event.target.value)}>
          <option value="">Seleccioná</option>
          {data?.professionals.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select>
      </label>
      <label>
        Prestación
        <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
          <option value="">Seleccioná</option>
          {data?.services.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select>
      </label>
      <form onSubmit={(event) => void submit(event)}>
        <label>Nombre<input required value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} /></label>
        <label>Apellido<input required value={form.apellido} onChange={(event) => setForm({ ...form, apellido: event.target.value })} /></label>
        <label>Teléfono<input value={form.telefono} onChange={(event) => setForm({ ...form, telefono: event.target.value })} /></label>
        <label>Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
        <label><input type="checkbox" checked={form.whatsapp} onChange={(event) => setForm({ ...form, whatsapp: event.target.checked })} /> Acepto recibir mensajes por WhatsApp</label>
        <label>
          Horario
          <select required value={slot} onChange={(event) => setSlot(event.target.value)} disabled={loading}>
            <option value="">Seleccioná</option>
            {data?.slots.map((item) => <option key={item} value={item}>{new Date(item).toLocaleString("es-AR")}</option>)}
          </select>
        </label>
        <button type="submit" disabled={loading}>Solicitar turno</button>
      </form>
      {actionToken && (action === "reprogramar" || !action) && (
        <button type="button" disabled={loading || !slot} onClick={() => void reschedule()}>
          Reprogramar turno
        </button>
      )}
    </main>
  );
}
