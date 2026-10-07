# Flujos Principales

Cada flujo se documenta extremo a extremo, mostrando interacciones entre componentes.

## Flujo 1: Reserva pública con seña (camino feliz)

**Disparador**: el paciente abre el link `/r/:slug`.
**Actor**: paciente (sin cuenta).

**Pasos**:
1. Frontend público pide disponibilidad → API calcula huecos (prestación + profesional + bloqueos + antelación).
2. Paciente elige hueco y deja datos + acepta opt-in WhatsApp.
3. API crea turno `pendiente_confirmacion` + token público; si la prestación exige seña, crea preferencia de Mercado Pago y devuelve `checkout_url`.
4. Paciente paga → webhook MP acredita seña → API confirma turno y encola WhatsApp de confirmación.
5. Worker envía recordatorios T-48h/T-24h; el paciente confirma con un toque → turno `confirmado`.

**Diagrama de secuencia** (ASCII):
```
Paciente → Frontend público → API → DB (turno pendiente + seña pendiente)
Paciente → Mercado Pago → (webhook) API → DB (seña acreditada, turno confirmado)
API → Redis (encolar WhatsApp) → Worker → Proveedor WhatsApp → Paciente
                                         ← estado entregada → DB
```

**Casos de error**:
- Pago no acreditado en 30 min → turno sigue pendiente; job lo libera y avisa. **Suposición:** 30 min; validar.
- Webhook MP duplicado → idempotencia por `mp_payment_id`.
- Proveedor WhatsApp caído → envío queda `encolada` con reintento (RN-GL-03); el turno igual queda confirmado.

## Flujo 2: Cancelación y lista de espera automática

**Disparador**: paciente (link) o recepción cancela un turno.
**Actor**: paciente o recepcionista.

**Pasos**:
1. API valida antelación contra config del tenant (RN-AG-01/02). Fuera de término → error + oferta de reprogramar.
2. Si aplica, seña pasa a saldo a favor o se pierde según política (RN-CO-03).
3. Turno → `cancelado`; el hueco queda libre.
4. Motor de lista de espera busca el primer `activa` compatible → estado `ofrecida` + WhatsApp con TTL.
5. Acepta → turno asignado (arrastra seña si corresponde); declina/vence → siguiente en lista.

**Casos de error**:
- Nadie en lista → hueco libre visible en agenda para carga manual.
- Paciente sin opt-in → se salta (RN-PA-01) y se registra el motivo.

## Flujo 3: Atención y registro clínico mínimo

**Disparador**: el paciente se presenta (turno → `presente`).
**Actor**: odontólogo.

**Pasos**:
1. Odontólogo abre ficha: datos + evoluciones previas + adjuntos + presupuestos/saldo.
2. Registra evolución (motivo, detalle, firma simple) → auditoría (RN-GL-02).
3. Si corresponde, crea/ajusta presupuesto simple → alimenta saldo/deuda.
4. Recepción/dueño registra el cobro → caja del día.

**Casos de error**:
- Adjunto pesado → límite configurable (defecto 10 MB) con mensaje claro. **Suposición:** 10 MB.

## Flujo 4: Auth multi-rol (incluye "todo en una persona")

**Disparador**: login con email + password.
**Actor**: recepcionista/odontólogo/dueño.

**Pasos**:
1. API valida credenciales → emite access (15 min) + refresh rotativo con `tenant_id` + roles.
2. Frontend deriva permisos (unión de roles) y muestra agenda/ficha/caja según corresponda.
3. Refresh reuse → revocación de familia (RN-AU-02).

**Casos de error**:
- Credenciales inválidas → 401 genérico (sin revelar si el email existe).
- Usuario inactivo → 403 con contacto del dueño del tenant.

## Flujo 5: Recordatorios programados (worker)

**Disparador**: scheduler Redis (cada 15 min).
**Actor**: sistema.

**Pasos**:
1. Scheduler selecciona turnos en ventana T-48h/T-24h sin recordatorio enviado y con opt-in.
2. Encola un job por envío → worker llama al proveedor WhatsApp → guarda `provider_msg_id` + costo estimado.
3. Fallo → reintento exponencial (3 intentos) → fallback email si hay (RN-PA-04) → estado `fallida` visible para recepción con botón reintentar.

**Casos de error**:
- Caída del proveedor → backoff; nada se pierde (cola persistente en Redis con persistencia AOF). **Suposición:** AOF activado; costo operativo mínimo.
