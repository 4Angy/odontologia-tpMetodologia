# Reglas de Negocio

Cada regla tiene un código único `RN-{DOMINIO}-{NN}` para trazabilidad. Los códigos se citan en `06_funcionalidades.md` y en errores API.

## Dominio: Agenda y turnos (RN-AG)

- **RN-AG-01**: un turno no puede cancelarse con menos antelación que la configurada (defecto 24h). Intentarlo devuelve error trazable y ofrece reprogramar. — Acuerdo de discovery; el valor es configurable por tenant, nunca constante quemada.
- **RN-AG-02**: la antelación mínima de cancelación es configurable por tenant (horas, entero ≥ 0). Solo el rol `dueno` la modifica; el cambio rige para turnos futuros, no retroactivo.
- **RN-AG-03**: no existen solapamientos por profesional/sillón: dos turnos del mismo profesional no pueden superponerse. La reserva que colisiona se rechaza con huecos alternativos sugeridos.
- **RN-AG-04**: los sobreturnos son explícitos (flag + motivo), nunca una colisión silenciosa; requieren rol con permiso de agenda.
- **RN-AG-05**: reprogramar arrastra la seña acreditada al nuevo turno (no se cobra dos veces). Si el nuevo turno no requiere seña, la seña queda como saldo a favor.
- **RN-AG-06**: el link público de reserva respeta bloqueos, duración por prestación y antelación mínima de reserva (configurable, defecto 2h). **Suposición:** defecto 2h; validar en Sprint 1.
- **RN-AG-07**: todo turno nacido de reserva pública entra en `pendiente_confirmacion` hasta confirmación (automática si hay seña acreditada, o manual por recepción/paciente).

## Dominio: Pacientes y comunicación (RN-PA)

- **RN-PA-01**: WhatsApp solo a pacientes con opt-in explícito y teléfono E.164 válido. Sin opt-in no hay envíos (ni siquiera transaccionales). — Base legal Ley 25.326.
- **RN-PA-02**: cada paciente tiene un único teléfono WhatsApp activo; el cambio de número invalida tokens/pendientes asociados al anterior.
- **RN-PA-03**: los recordatorios se envían en la ventana T-48h y T-24h por defecto (configurable); no se envía más de 1 mensaje por ventana y turno (anti-spam).
- **RN-PA-04**: el fallback a email solo dispara si el envío WhatsApp falla o no hay opt-in WhatsApp pero sí email.

## Dominio: Cobros y señas (RN-CO)

- **RN-CO-01**: "facturación" en v1 = caja manual. El sistema no emite comprobantes fiscales ni integra AFIP/ARCA. La UI lo declara para no defraudar expectativas (supuesto sin probar — ver SU-03).
- **RN-CO-02**: la seña por Mercado Pago es opcional por tenant y por prestación; si está activa y es requerida, la reserva pública no confirma sin seña acreditada (webhook MP).
- **RN-CO-03**: devolución de seña parametrizable: `no_devuelve | devuelve_50 | devuelve_100` según antelación cumplida (RN-AG-01). Defecto: si cancela en término, seña como saldo a favor; si cancela fuera de término, se pierde. **Suposición:** este defecto; el dueño lo configura.
- **RN-CO-04**: el cierre de caja es diario, inmutable una vez cerrado (solo nota de ajuste con auditoría, nunca edición).
- **RN-CO-05**: el saldo/deuda del paciente es siempre derivado (cobros − presupuestos/señas aplicadas); ningún endpoint lo edita directo.

## Dominio: Autenticación y tenancy (RN-AU)

- **RN-AU-01**: todo dato de negocio pertenece a un tenant y todo acceso se filtra por el `tenant_id` del JWT. Sin tenant no hay respuesta (403, no 404 con fuga).
- **RN-AU-02**: access token corto (15 min) + refresh rotativo (7 días); refresh reuse = revocación de la familia de tokens.
- **RN-AU-03**: las acciones del paciente por link público usan token único por turno con expiración (defecto 72h post-turno), no JWT. **Suposición:** 72h; validar.
- **RN-AU-04**: un usuario puede acumular los 3 roles; el permiso efectivo es la unión. Nada en el flujo exige tres personas distintas.

## Dominio: Excepciones globales

- **RN-GL-01**: todo error de negocio devuelve `code` = código RN que lo causó + mensaje en español-AR mostrable.
- **RN-GL-02**: toda mutación escribe auditoría mínima (quién/cuándo/qué cambió) consultable por el dueño.
- **RN-GL-03**: ninguna integración externa (WhatsApp/MP) bloquea el flujo local: si el proveedor cae, la operación local se completa y el envío queda `encolada` con reintento exponencial (ver `07_flujos_principales.md`).
- **RN-GL-04**: la exportación del tenant (CSV/Excel/PDF) incluye todo lo propio sin lock-in; es derecho del cliente, no favor (diferencial "transparencia radical").
