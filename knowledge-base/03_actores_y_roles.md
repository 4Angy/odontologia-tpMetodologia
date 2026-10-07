# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Recepcionista | Agenda turnos y gestiona la agenda del día | SPA: agenda día/semana, alta de pacientes, confirmaciones, lista de espera, cobro de seña |
| Odontólogo | Registra la atención y consulta la ficha del paciente | SPA: ficha + evoluciones + adjuntos, presupuestos simples, su propia agenda |
| Dueño | Cobra, controla la caja y mira los números | SPA: caja/cierre, saldos/deudas, números básicos, gestión de usuarios del tenant |
| Paciente (externo, sin cuenta) | Reserva, confirma, cancela, reprograma | Link público de reserva 24/7 + botones en mensajes de WhatsApp (sin login) |
| Sistema/Worker | Dispara recordatorios, vencimientos 24h, lista de espera | Jobs Redis + webhooks WhatsApp/MP (sin UI) |

> Restricción estructural confirmada: los tres roles internos suelen ser la misma persona (consultorio de 1–2 personas). El modelo de roles **no asume tres personas distintas**: un usuario puede tener los tres roles a la vez y la UI no exige "cambiar de usuario" para hacer tareas cruzadas.

## RBAC — Matriz de permisos

Roles: `recepcion` · `odontologo` · `dueno`. `dueno` incluye todo. Un usuario puede acumular roles.

| Recurso | recepcion | odontologo | dueno |
|---------|-----------|------------|-------|
| Agenda (crear/editar turnos, bloqueos, sobreturnos) | CRUD | R (sus turnos) + bloqueos propios | CRUD |
| Reserva pública (link) | configura | — | configura |
| Pacientes (altas, datos contacto) | CRUD | R + evoluciones CRUD | R |
| Evoluciones/atenciones | — | CRUD (propias) | R |
| Presupuestos simples | R | CRUD | CRUD |
| Cobros/señas/caja | crear cobros | — | CRUD + cierre |
| Deudas/saldos | R | — | CRUD |
| Recordatorios/notificaciones | disparar/reintentar | — | ver consumo |
| Usuarios del tenant | — | — | CRUD + asignar roles |
| Configuración (antelación cancelación, señas, plantillas) | — | — | CRUD |
| Exportación CSV/Excel/PDF | propios módulos | propios módulos | todo |
| Auditoría | — | — | R |

**Suposición:** el dueño puede delegar "encargado" otorgando rol `dueno` a otra persona; no hay rol intermedio en v1 (se crea solo si la validación lo pide — ver SU-02 en `09_decisiones_y_supuestos.md`).

## Rutas públicas

Sin autenticación (rate-limit + token firmado/captcha donde aplique):

- `GET /r/:tenantSlug` — página de reserva pública del consultorio.
- `POST /public/reservar` — crear solicitud de turno (genera turno `pendiente_confirmacion` o aplica seña si está configurada).
- `POST /public/turnos/:token/confirmar|Cancelar|reprogramar` — acciones del paciente desde el link de WhatsApp (token único por turno, con expiración).
- `POST /webhooks/whatsapp` — eventos del proveedor WhatsApp.
- `POST /webhooks/mercadopago` — notificaciones de pago de seña.
- `GET /health` — liveness para el deploy.
