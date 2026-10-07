# Modelo de Datos

## Dominios

- **Tenancy/identidad**: tenants (consultorios), usuarios, roles, sesiones.
- **Pacientes**: ficha, evoluciones mínimas, adjuntos, consentimientos simples.
- **Agenda**: profesionales/sillones, prestaciones (duración), turnos, bloqueos, lista de espera, reserva pública.
- **Cobros**: señas (MP), cobros manuales, caja/cierres, deudas/saldos, presupuestos simples.
- **Notificaciones**: plantillas, envíos WhatsApp/email, opt-ins, consumo/costos.

## ERD (Entity Relationship Diagram)

```
tenant 1───* usuario          tenant 1───* paciente 1───* evolucion
  │              │ (roles N───* por usuario)  │ 1───* adjunto
  │              │                            │ 1───* presupuesto 1───* presupuesto_item
  │              │
  │              ├───* profesional ───┐
  │              ├───* prestacion ────┤
  │              ├───* turno ─────────┤ (turno → paciente, profesional, prestacion, estado)
  │              ├───* bloqueo ───────┘ (bloqueo → profesional/sillon, rango)
  │              ├───* lista_espera (→ paciente, prestacion/profesional, prioridad)
  │              ├───* cobro (→ paciente, turno?, medio)
  │              ├───* senia (→ turno, paciente, mp_payment_id)
  │              ├───* cierre_caja (→ cobros del día)
  │              └───* notificacion_envio (→ paciente, turno?, canal, plantilla, costo)
paciente 1───* optin (canal, estado)     tenant 1───* config (antelacion_hs, senia_monto, plantillas)
```

Toda tabla de negocio lleva `tenant_id` NOT NULL + FK a `tenant`. Unicidades y búsquedas siempre compuestas con `tenant_id`.

## Entidades

### tenant
- Atributos: `id` (uuid PK), `slug` (text unique, para link público), `nombre` (text), `email_contacto`, `tz` (text, default `America/Argentina/Buenos_Aires`), `created_at`
- Relaciones: 1───* con todo lo de negocio
- Constraints: `slug` kebab-case único global
- Índices: `slug`

### usuario
- Atributos: `id`, `tenant_id` FK, `nombre`, `email` (unique por tenant), `password_hash`, `roles` (array enum: recepcion/odontologo/dueno), `activo` (bool), `created_at`
- Relaciones: *───* roles (embebido como array en v1); *───1 tenant
- Constraints: un usuario pertenece a un solo tenant en v1
- Índices: `(tenant_id, email)`

### paciente
- Atributos: `id`, `tenant_id`, `nombre`, `apellido`, `dni` (nullable), `telefono` (E.164, para WhatsApp), `email` (nullable), `fecha_nac` (nullable), `notas`, `saldo` (derivado, no editable directo), `created_at`
- Relaciones: 1───* evolucion, adjunto, turno, cobro, optin
- Constraints: `telefono` requerido si opt-in WhatsApp activo (RN-PA)
- Índices: `(tenant_id, apellido)`, `(tenant_id, telefono)`, `(tenant_id, dni)`

### evolucion (HCE mínima v1)
- Atributos: `id`, `tenant_id`, `paciente_id` FK, `odontologo_id` FK, `fecha`, `motivo`, `detalle` (text), `firma_simple` (bool + timestamp — alcance legal declarado honestamente, no firma digital Ley 25.506)
- Relaciones: *───1 paciente, *───1 usuario(odontólogo)
- Índices: `(tenant_id, paciente_id, fecha desc)`

### profesional / prestacion
- profesional: `id`, `tenant_id`, `usuario_id` (nullable — un profesional puede no tener login), `nombre`, `color_agenda`, `activo`
- prestacion: `id`, `tenant_id`, `nombre`, `duracion_min` (int), `precio_ref` (nullable, para presupuesto/seña), `activa`

### turno
- Atributos: `id`, `tenant_id`, `paciente_id`, `profesional_id`, `prestacion_id` (nullable), `inicio`/`fin` (timestamptz), `estado` (enum: `pendiente_confirmacion|confirmado|presente|ausente|cancelado|reprogramado`), `origen` (mostrador/reserva_publica/lista_espera), `token_publico` (unique, para acciones sin login), `senia_id` (nullable), `created_at`
- Constraints: sin solape por profesional (exclusión en app + índice); `fin > inicio`; cancelación validada contra config (RN-AG-01)
- Índices: `(tenant_id, profesional_id, inicio)`, `(tenant_id, inicio)`, `token_publico`

### lista_espera
- Atributos: `id`, `tenant_id`, `paciente_id`, `profesional_id` (nullable = cualquiera), `prestacion_id` (nullable), `prioridad` (int/fecha), `estado` (`activa|ofrecida|convertida|vencida`), `created_at`
- Índices: `(tenant_id, estado, prioridad)`

### senia / cobro / cierre_caja
- senia: `id`, `tenant_id`, `turno_id`, `paciente_id`, `monto`, `mp_preference_id`, `mp_payment_id` (nullable), `estado` (`pendiente|acreditada|devuelta|aplicada`), timestamps
- cobro: `id`, `tenant_id`, `paciente_id`, `turno_id` (nullable), `monto`, `medio` (efectivo/transferencia/mp/otro), `concepto`, `usuario_id` (quién cobró), `fecha`
- cierre_caja: `id`, `tenant_id`, `fecha`, `total_efectivo`, `total_transferencia`, `total_mp`, `observaciones`, `usuario_id`
- Índices: `(tenant_id, fecha)`, `(tenant_id, paciente_id)`

### notificacion_envio / optin
- notificacion_envio: `id`, `tenant_id`, `paciente_id`, `turno_id` (nullable), `canal` (whatsapp/email), `plantilla`, `estado` (`encolada|enviada|entregada|fallida`), `costo_estimado` (nullable), `provider_msg_id`, `created_at`
- optin: `id`, `tenant_id`, `paciente_id`, `canal`, `estado` (bool), `updated_at`
- Índices: `(tenant_id, created_at)`, `(tenant_id, estado)` para reintentos

## Seed data inicial

- Un `tenant` demo (`slug: demo`) + 3 usuarios demo (uno por rol y uno con los 3 roles para probar el caso "todo en una persona").
- Catálogo mínimo de `prestacion` (limpieza 30', consulta 20', arreglo 45', conducto 60' — **Suposición:** duraciones editables, solo seed).
- `config` por defecto: `antelacion_cancel_hs = 24`, `senia_requerida = false`, recordatorios `T-48h + T-24h`.
- Plantillas WhatsApp base (confirmación, recordatorio, cancelación, lista de espera, seña) en español-AR.
