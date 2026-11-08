# Proposal

## Why

El ausentismo es la pérdida económica más directa del consultorio y el recordatorio
automático es el feature que la ataca (US-003). C-07 y C-08 ya dejan el turno creado,
confirmado o `pendiente_confirmacion`, con opt-in registrado y tokens públicos
revocables; falta el motor que **dispare** el mensaje en las ventanas T-48h/T-24h,
resista la caída del proveedor sin perder la intención de envío, respete el anti-spam
de RN-PA-03 y haga visible el costo por tenant (US-012 CA-1). Sin este change, el
opt-in y los tokens de C-04/C-08 no se usan y el flujo 5 de la KB queda sin
implementación.

## What Changes

- Crear el módulo `notificaciones` con dos entidades nuevas: `notificacion_envio`
  (la cola durable) y `plantilla` (textos es-AR por canal y tenant).
- Agregar un scheduler de recordatorios al worker existente: cada 15 minutos
  selecciona turnos dentro de las ventanas configurables, verifica opt-in y encola
  como máximo un envío por turno y ventana (RN-PA-03).
- Agregar un sender al mismo worker: toma envíos `encolada` con
  `FOR UPDATE SKIP LOCKED`, llama al proveedor detrás de `WhatsAppClient`, registra
  `provider_msg_id`, `intentos` y `costo_estimado_centavos`, y reintenta con backoff
  1/5/15 min.
- Aplicar RN-PA-04: al agotar los tres intentos de WhatsApp, o cuando el paciente
  tiene email y no tiene opt-in de WhatsApp, se encola un envío `canal="email"` en
  lugar de enviarlo inline.
- Registrar el acuse del paciente sin tocar la máquina de estados: un turno que ya
  está `confirmado` y recibe el click del recordatorio guarda
  `confirmado_paciente_at`; un turno `pendiente_confirmacion` conserva la transición
  de C-08 a `confirmado`.
- Exponer `POST /webhooks/whatsapp` (verificación de firma + challenge de Meta) y
  hacer idempotente por `provider_msg_id` el avance de estado, sin retrocesos por
  eventos desordenados.
- Exponer `GET /notificaciones/consumo` (dueño), `GET /notificaciones/envios` y
  `POST /notificaciones/envios/{id}/reintentar` (recepción/dueño) y
  `POST /notificaciones/test` (recepción/dueño, rate-limited).
- Agregar migración `012_notificaciones` reversible: tablas, índices, unicidades y
  columnas de configuración (`recordatorio_1_hs`, `recordatorio_2_hs`,
  `whatsapp_costo_centavos`) y `turno.confirmado_paciente_at`.
- Frontend mínimo: panel de consumo/costo para el dueño y página pública que resuelve
  el link de confirmación del mensaje (GET del navegador → POST de C-08).

## Capabilities

### New Capabilities

- `notificaciones/motor-envios`: selección de turnos por ventana y opt-in, cola
  durable, envío, reintentos, fallback email, webhook idempotente, acuse del paciente
  y consumo/costo por tenant.

### Modified Capabilities

- `agenda/reserva-publica`: la acción pública `confirmar` deja de fallar sobre un
  turno ya `confirmado` y pasa a registrar el acuse del paciente sin cambiar el
  estado; sobre `pendiente_confirmacion` mantiene la transición a `confirmado`.
- `agenda/turnos-internos`: la representación del turno y la agenda interna exponen
  `confirmado_paciente_at` como dato de solo lectura; la máquina de estados no cambia.

## Impact

- Backend: nuevo módulo `app/modules/notificaciones/` (modelos, repositorios
  tenant-scoped, servicios, router, adapter de proveedor); `app/worker/main.py` deja
  `JOBS=()` y registra `notificaciones.scheduler` y `notificaciones.sender`.
- Persistencia: migración `012_notificaciones` (siguiente libre; `011_reserva_publica_tokens`
  ya pertenece a C-08). Reversible con `downgrade` probado en PostgreSQL 16.
- Configuración: `WHATSAPP_PROVIDER=official`, `WHATSAPP_API_TOKEN`,
  `WHATSAPP_PHONE_ID`, `WHATSAPP_WEBHOOK_SECRET`, `SMTP_URL` y `PUBLIC_BASE_URL` ya
  existen en `core/config.py`; se agregan las validaciones de arranque que faltan
  para el webhook.
- Redis: pasa a ser **coordinación, no cola** (lock del tick y pre-chequeo de
  deduplicación). El estado del envío vive en Postgres. Desvío explícito respecto del
  §Flujo 5 de la KB, justificado en `design.md` con evidencia del MCP `redis`.
- RBAC: `PERMISOS_RECORDATORIOS` ya declara recepción/dueño; el consumo queda
  restringido a dueño.
- Datos: solo pacientes sintéticos; ningún número real ni credencial en el repo (R14).
- Dependencias: C-07 (turnos y estados), C-08 (tokens y acción pública), C-04
  (paciente y opt-in). Habilita C-10 (lista de espera reutiliza el motor).
