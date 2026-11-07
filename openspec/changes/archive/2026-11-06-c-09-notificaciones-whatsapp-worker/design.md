# Design

## Context

C-07 entrega turnos con estados, colisiones y agenda; C-08 entrega tokens públicos
opacos por propósito (`confirm`/`cancel`/`reschedule`), TTL de 72 h, revocación y la
acción pública `POST /public/turnos/{token}/confirmar`; C-04 entrega paciente,
teléfono E.164 y una tabla `optin` por canal. El worker de C-01 corre un tick cada
15 segundos con `JOBS=()` y conecta Redis de forma best-effort. La cadena Alembic
está en `011_reserva_publica_tokens`, así que C-09 usa `012_notificaciones`.

Hay un hueco de dominio que este change debe cerrar: los turnos internos nacen
`confirmado` (spec `agenda/turnos-internos`), mientras US-003 CA-2 pide que el
paciente confirme con un toque y "el turno pase a `confirmado`". Para un turno ya
confirmado esa frase no describe ninguna transición. C-09 define ese caso como
**acuse del paciente** y lo registra sin reabrir la máquina de estados de C-07.

ADR-001 ya fijó `WHATSAPP_PROVIDER=official` (Cloud API de Meta) con un único
adapter detrás de una interfaz; `gateway` queda como camino de v2 sin implementar.
El volumen supuesto es 300–3.000 mensajes/mes por tenant (≈0,1 mensaje/minuto),
por lo que la latencia no es un requisito y la corrección sí.

## Goals / Non-Goals

**Goals:**

- Disparar recordatorios en ventanas configurables (T-48h/T-24h por defecto),
  respetando opt-in y anti-spam (RN-PA-01, RN-PA-03).
- Garantizar que la intención de envío sobreviva a caídas del proveedor, del worker
  y de Redis, sin duplicar mensajes (RN-GL-03, R8).
- Aplicar el fallback a email como parte del mismo pipeline (RN-PA-04).
- Registrar el acuse del paciente y exponerlo en la agenda sin cambiar el estado.
- Hacer visible el consumo y el costo por tenant, en centavos (US-012 CA-1, R5).
- Dejar la verificación de cada escenario escrita en `tasks.md`, ejecutable sin
  credenciales reales de Meta.

**Non-Goals:**

- Lista de espera y oferta automática de huecos; pertenece a C-10 (reutiliza el motor).
- Cobro de señas y webhooks de Mercado Pago; pertenece a C-12.
- Onboarding real de WABA y aprobación de plantillas ante Meta; se documenta como
  runbook y se controla con un interruptor de despliegue.
- Reemplazar el rate limiter in-memory; el swap a Redis sigue siendo C-13.
- Migrar a SQLAlchemy async; el trigger de re-evaluación sigue siendo C-13.
- Panel frontend completo de analítica; este change entrega el endpoint y una vista
  mínima de consumo.

## Decisions

### D1 — "Confirmar" en el recordatorio significa acuse del paciente

El click del paciente sobre un turno `confirmado` escribe
`turno.confirmado_paciente_at` y **no** cambia `turno.estado`. Sobre un turno
`pendiente_confirmacion` se conserva la transición de C-08 a `confirmado`.

Se elige sobre las alternativas porque: (a) es la única que conserva la señal que
justifica el feature —saber quién dijo "voy"— sin reabrir C-07; (b) un estado nuevo
`confirmado_por_paciente` obligaría a revisar transiciones, permisos y métricas de
un change ya archivado; (c) mandar link solo a `pendiente_confirmacion` dejaría la
mayoría de los turnos sin acción útil, porque el turno interno nace `confirmado`.
La columna es de solo lectura para la agenda: ninguna acción interna la escribe.

### D2 — La cola es la tabla `notificacion_envio`, no Redis

El scheduler inserta la fila del envío y el sender la reclama con
`SELECT ... FOR UPDATE SKIP LOCKED`. Redis no guarda estado de negocio.

Evidencia recogida con el MCP `redis` sobre la instancia de desarrollo:

| Consulta | Resultado | Lectura |
|---|---|---|
| `redis_health` | Redis 7.4.11, `standalone`, `total_keys = 0` | instancia viva y vacía: no hay estado previo que reconciliar |
| `CONFIG GET appendfsync` | `everysec` | hasta ~1 s de escrituras se pierde ante un corte |
| `CONFIG GET maxmemory-policy` | `noeviction` | al llenarse la memoria, las escrituras fallan en vez de desalojar |
| `maxmemory` | `0` (sin límite) | el límite es implícito: el día que se fije, cambia la semántica |

Una cola que no debe perder mensajes no puede vivir en un store con esas dos
propiedades. Además, dos fuentes de verdad (fila + mensaje) obligan a reconciliar
cuando un `XACK` se pierde, que es el bug más caro de esta feature. La tabla
también es lo que necesita el panel de US-012, que es SQL puro.

**Desvío explícito respecto de la KB.** `knowledge-base/07` §Flujo 5 dice
"cola persistente en Redis con AOF". C-09 no lo implementa literalmente: usa la
fila como cola y Redis como coordinación. El requisito que la KB exige (RN-GL-03:
"si el proveedor cae, la operación local se completa y el envío queda `encolada`
con reintento") se cumple igual y de forma más fuerte: la fila sobrevive reinicios
y `FLUSHALL`. El desvío queda registrado aquí y en el informe de aplicación.

### D3 — Lock del tick: Redis con degradación a Postgres

El scheduler corre cada 15 minutos, pero el tick del worker es de 15 segundos. La
primera ejecución del intervalo toma `SET tick:notificaciones:{tenant} NX EX 840`;
las siguientes ven la clave, no hacen nada, y la clave expira antes del próximo
intervalo.

Si Redis no está disponible, el scheduler **no se detiene**: cae a
`pg_try_advisory_lock(hashtext('notificaciones:' || tenant_id))`. El lock es
coordinación, no estado; perderlo no debe apagar los recordatorios. Esto es
consistente con el arranque best-effort que ya tiene el worker.

### D4 — Idempotencia y anti-spam se garantizan en Postgres

Dos restricciones hacen el trabajo:

- `UNIQUE (tenant_id, turno_id, ventana, canal)` → anti-spam de RN-PA-03 e
  idempotencia del scheduler. Un segundo tick choca y se descarta con
  `ON CONFLICT DO NOTHING`.
- `UNIQUE (tenant_id, provider_msg_id)` parcial (`provider_msg_id IS NOT NULL`) →
  idempotencia del webhook de R8.

Redis puede usarse como pre-chequeo barato (`SET NX`), pero **nunca** como
garantía: si se pierde, la restricción de la base sigue evitando el duplicado. Se
prefiere esto a deduplicar solo en Redis porque un `FLUSHALL` duplicaría mensajes
enviados a pacientes reales, con costo y riesgo de reclamo.

### D5 — Un adapter y un fake, no `httpx` suelto

`WhatsAppClient` es un `Protocol` con dos implementaciones: `CloudApiClient`
(httpx contra Meta, timeout explícito, mapeo de errores) y `FakeClient` (tests y
desarrollo). El worker depende del protocolo, no de httpx.

`WHATSAPP_PROVIDER` no cambia: `official` sigue siendo el único valor
implementado. El fake se inyecta por dependency override, mismo patrón que usan
las pruebas de agenda con reloj y sesión. `httpx.MockTransport` cubre los códigos
`200`, `429` y `500` del adapter real sin red, para que el mapeo de errores
transitorios vs. permanentes también tenga prueba.

Se elige sobre interceptar `httpx` en cada test porque governance ALTO pide una
frontera única para lo que puede fallar, y porque el fallback, el costo y el
mapeo de errores necesitan un solo lugar donde vivir.

### D6 — Se reutiliza el token de C-08 y se cierra el hueco GET/POST

El mensaje incluye `{PUBLIC_BASE_URL}/r/{tenant_slug}/confirmar?token={token}`. El
token es el de C-08 (`purpose="confirm"`, hash persistido, TTL 72 h, revocación por
cambio de teléfono). La página pública hace el `POST` a
`/public/turnos/{token}/confirmar` al cargar y muestra el resultado.

El motivo es concreto: un link de WhatsApp se abre con un `GET` del navegador o de
la app, y la ruta de C-08 es `POST` con body. Sin la página, el "un toque" no
funciona. Se descarta un `GET` que mute estado porque el prefetch de clientes de
correo y los crawlers confirmarían turnos sin intervención del paciente.

### D7 — El fallback a email es otra fila del mismo motor

Al agotar los tres intentos de WhatsApp, o cuando el paciente tiene email y no
tiene opt-in de WhatsApp, se inserta una fila `canal="email"`, `estado="encolada"`.
El mismo sender la toma y la entrega por SMTP.

Enviar el email inline al detectar el fallo pierde la intención si el proceso
muere entre el fallo y el SMTP, y deja al botón "reintentar" de recepción sin nada
que reintentar. La fila encolada cumple RN-GL-03 al pie de la letra.

### D8 — Máquina de estados del envío, monotónica

```
encolada ──> enviada ──> entregada
    │            │
    ├──> fallida (3 intentos) ──> encolada (reintento manual)
    ├──> omitida  (sin canal habilitado, RN-PA-01)
    └──> cancelada (turno cancelado/reprogramado, opt-in revocado)
```

Ranking de eventos del proveedor: `enviada < entregada`; `fallida` solo aplica si
no hubo `entregada`; `omitida` y `cancelada` son terminales para el scheduler. Meta
puede entregar eventos desordenados, así que el webhook nunca retrocede el estado.

### D9 — El costo es un entero en centavos, congelado al enviar

`notificacion_envio.costo_estimado_centavos` se copia desde
`config.whatsapp_costo_centavos` en el instante del envío. Así, cambiar la tarifa
del tenant no reescribe el histórico ni falsea el panel. El email se registra con
costo `0`. No se usa `float` en ningún punto (R5); el formateo ARS es de la vista.

### D10 — Ventanas configurables por tenant y columna `ventana`

`config.recordatorio_1_hs` (default 48) y `config.recordatorio_2_hs` (default 24).
Cada fila guarda `ventana ∈ {t-48h, t-24h}`, que es lo que hace verificable el
anti-spam y testeable el caso "segundo tick no reenvía". Si una ventana tiene el
mismo valor que la otra, se envía una sola vez (la restricción única evita el
duplicado por ventana, y el scheduler deduplica por instante de envío).

### D11 — Webhook autenticado, idempotente y con challenge

`GET /webhooks/whatsapp` responde el `hub.challenge` cuando
`hub.verify_token` coincide con `WHATSAPP_VERIFY_TOKEN`. `POST /webhooks/whatsapp`
valida `X-Hub-Signature-256` con HMAC-SHA256 sobre el cuerpo crudo usando
`WHATSAPP_APP_SECRET`, y rechaza sin firma válida. El procesamiento hace
`INSERT ... ON CONFLICT DO NOTHING` sobre `provider_msg_id` y aplica el ranking de
D8. Un duplicado responde `2xx` para cortar los reintentos del proveedor.

### D12 — El panel es una agregación SQL, no una tabla materializada

`GET /notificaciones/consumo?desde&hasta` agrupa por canal y estado con
`COUNT(*)` y `SUM(costo_estimado_centavos)` sobre el índice
`(tenant_id, created_at)`. Con este volumen, una vista materializada sería estado
derivado que hay que mantener sin beneficio.

### D13 — Cancelación de pendientes como efecto de dominio

Cancelar o reprogramar un turno, o revocar el opt-in, actualiza a `cancelada` los
envíos `encolada` del turno con `motivo_code` (`turno_cancelado`,
`turno_reprogramado`, `optin_revocado`). No se borra nada: la intención queda
auditada. El sender vuelve a verificar el estado del turno antes de enviar, para
cubrir la carrera entre la cancelación y el envío.

### D14 — El destinatario no se duplica en la fila de envío

La fila guarda `paciente_id` y el canal; el número o el email se resuelven al
momento de enviar desde `paciente` + `optin`. Guardar el destino duplicaría datos
personales y quedaría desactualizado si el paciente cambia de teléfono (RN-PA-02).
La auditoría registra el evento con el hash del destino, como ya hace C-04.

### D15 — Interruptor de despliegue y plantillas inactivas por defecto

Meta exige plantillas preaprobadas para mensajes iniciados por el negocio. Las
plantillas se siembran `activa=false` y el scheduler solo encola plantillas
activas. Además, `NOTIFICACIONES_ENABLED=false` por defecto: el motor arranca en
modo pasivo hasta que el tenant tenga WABA y plantillas aprobadas. Sin esto, un
despliegue en producción intentaría enviar con plantillas no aprobadas y quemaría
la reputación del número.

### D16 — Estados `omitida` y `cancelada` existen para poder auditar

La KB pide "registrar el motivo" cuando no se envía (RN-PA-01). En vez de una tabla
de descartes, el envío se registra `omitida` con `motivo_code`. El panel excluye
`omitida` y `cancelada` del costo, pero las muestra como volumen, que es lo que
permite explicar por qué un paciente no recibió nada.

## Data Model

### `notificacion_envio` (nueva)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `varchar(64)` PK | uuid4 string, igual que el resto del repo |
| `tenant_id` | `varchar(64)` FK `tenant.id` | NOT NULL, indexado (R1) |
| `paciente_id` | `varchar(64)` | NOT NULL, indexado |
| `turno_id` | `varchar(64)` | nullable: C-10 enviará sin turno |
| `canal` | `varchar(20)` | `whatsapp` \| `email` |
| `plantilla_codigo` | `varchar(60)` | NOT NULL |
| `ventana` | `varchar(10)` | `t-48h` \| `t-24h`, nullable |
| `estado` | `varchar(20)` | `encolada` \| `enviada` \| `entregada` \| `fallida` \| `omitida` \| `cancelada` |
| `motivo_code` | `varchar(40)` | `RN-PA-01`, `RN-PA-03`, `RN-PA-04`, `turno_cancelado`, `turno_reprogramado`, `optin_revocado`, `ventana_vencida` |
| `intentos` | `integer` | NOT NULL, default 0, `>= 0` |
| `next_attempt_at` | `timestamptz` | NOT NULL, UTC (R7) |
| `provider_msg_id` | `varchar(128)` | nullable |
| `costo_estimado_centavos` | `integer` | NOT NULL, default 0, `>= 0` (R5) |
| `ultimo_error_code` | `varchar(40)` | nullable, trazable (R9) |
| `enviado_at` / `entregado_at` | `timestamptz` | nullable, UTC |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

Restricciones e índices:

- `ux_notif_tenant_turno_ventana_canal (tenant_id, turno_id, ventana, canal)`
- `ux_notif_tenant_provider_msg (tenant_id, provider_msg_id) WHERE provider_msg_id IS NOT NULL`
- `ix_notif_tenant_estado_next (tenant_id, estado, next_attempt_at)` → reclamación del sender
- `ix_notif_tenant_created (tenant_id, created_at)` → panel de consumo
- `ck_notif_costo_no_negativo`
- `ck_notif_intentos_no_negativos`

### `plantilla` (nueva)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `varchar(64)` PK | |
| `tenant_id` | `varchar(64)` FK | NOT NULL, indexado |
| `codigo` | `varchar(60)` | `recordatorio`, `confirmacion`, `cancelacion`, `lista_espera`, `senia` |
| `canal` | `varchar(20)` | `whatsapp` \| `email` |
| `idioma` | `varchar(10)` | default `es-AR` |
| `asunto` | `varchar(200)` | nullable, solo email |
| `cuerpo` | `text` | NOT NULL, con placeholders `{{paciente}}`, `{{fecha}}`, `{{link}}` |
| `activa` | `boolean` | NOT NULL, default `false` (D15) |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

`UNIQUE (tenant_id, codigo, canal, idioma)`. El seed crea las cinco plantillas por
tenant demo en `es-AR`, con datos ficticios.

### Cambios en tablas existentes

- `config`: `recordatorio_1_hs integer NOT NULL DEFAULT 48`,
  `recordatorio_2_hs integer NOT NULL DEFAULT 24`,
  `whatsapp_costo_centavos integer NOT NULL DEFAULT 0`.
- `turno`: `confirmado_paciente_at timestamptz NULL`.

### API

| Método y ruta | Roles | Propósito |
|---|---|---|
| `GET /notificaciones/consumo?desde&hasta` | dueno | US-012 CA-1: mensajes y costo por canal/estado |
| `GET /notificaciones/envios?estado&turno_id` | recepcion, dueno | ver `fallida` y `omitida` con motivo |
| `POST /notificaciones/envios/{id}/reintentar` | recepcion, dueno | reintento manual solo desde `fallida` |
| `POST /notificaciones/test` | recepcion, dueno | envío de prueba auditado, rate-limited |
| `GET /webhooks/whatsapp` | — (Meta) | challenge de suscripción |
| `POST /webhooks/whatsapp` | — (Meta, firma) | estados de entrega idempotentes |

Todos los DTO son Pydantic v2 con `extra='forbid'` (R4) y ningún modelo ORM se
expone (R3). Los errores de negocio llevan `code` trazable a RN (R9).

### Integración con el worker

`backend/app/worker/main.py` pasa de `JOBS=()` a registrar dos jobs idempotentes
que se ejecutan en cada tick:

1. `notificaciones.scheduler` — si el lock del intervalo se obtiene, evalúa las
   dos ventanas de todos los tenants con `NOTIFICACIONES_ENABLED=true`.
2. `notificaciones.sender` — reclama hasta `N` envíos vencidos y los procesa.

El tick de 15 s y el lock de 840 s son la única coordinación temporal: no se agrega
un scheduler externo.

## Migration Plan

1. `012_notificaciones` (posterior a `011_reserva_publica_tokens`): crea `plantilla`
   y `notificacion_envio`, agrega `config.recordatorio_1_hs`,
   `config.recordatorio_2_hs`, `config.whatsapp_costo_centavos` y
   `turno.confirmado_paciente_at`, con índices y checks. `downgrade` elimina en
   orden inverso y debe probarse `upgrade head → downgrade 011 → upgrade head`
   contra PostgreSQL 16.
2. Seed de plantillas `es-AR` **inactivas** para el tenant demo, idempotente.
3. Desplegar backend con `NOTIFICACIONES_ENABLED=false`; el panel y los endpoints
   funcionan, el scheduler no encola.
4. Activar plantillas aprobadas por tenant y luego el interruptor. El primer envío
   real se hace con `POST /notificaciones/test` sobre un paciente sintético.
5. Rollback: apagar el interruptor, dejar que los envíos `encolada` expiren por
   `next_attempt_at` sin procesarse y ejecutar el downgrade solo si no hay filas
   dependientes. Los turnos y sus acuses se conservan.

## Verification with MCP

La preparación usó dos servidores MCP en tareas distintas, con estos resultados:

| Herramienta | Solicitud | Resultado | Qué aportó al change |
|---|---|---|---|
| `filesystem.read_text_file` | `knowledge-base/07_flujos_principales.md`, `05_reglas_de_negocio.md`, `06_funcionalidades.md` | Flujo 5, RN-PA-01/03/04, RN-GL-03, US-003, US-012 | fijó ventanas, reintentos, fallback y el alcance del panel |
| `filesystem.read_text_file` | `openspec/specs/agenda/reserva-publica/spec.md`, `agenda/turnos-internos/spec.md` | la confirmación pública solo existe para `pendiente_confirmacion`; el turno interno nace `confirmado` | originó D1 y el delta de `reserva-publica` |
| `redis.redis_health` | estado de la instancia de desarrollo | 7.4.11, AOF `everysec`, `noeviction`, `maxmemory 0`, 0 claves | justificó D2 (Redis no es cola) y dio la línea base del namespace |
| `redis.redis_command CONFIG GET appendfsync` / `maxmemory-policy` | verificar durabilidad real | `everysec` / `noeviction` | evidencia literal citada en D2, no una opinión |

Después de implementar, la misma integración se usa para verificar los escenarios
que dependen de Redis:

- `redis_key_info tick:notificaciones:{tenant}` → TTL entre 1 y 840 s mientras el
  intervalo está tomado, y clave ausente al vencer.
- `redis_scan` con `tick:*`, `dedupe:*` y `provider_msg_id:*` → confirma que el
  namespace no colisiona con otras integraciones.

## Risks / Trade-offs

- **[Desvío respecto de la KB]** → queda documentado (D2) con evidencia del MCP y
  la regla que sí se cumple (RN-GL-03). Riesgo de defensa en la cátedra: bajo.
- **[Plantillas no aprobadas por Meta]** → D15: interruptor apagado, plantillas
  inactivas y `POST /notificaciones/test` como único disparador inicial.
- **[Duplicado de mensajes]** → restricción única + `ON CONFLICT DO NOTHING` +
  prueba de dos schedulers concurrentes. Es el riesgo con costo real por mensaje.
- **[Costo estimado desactualizado]** → snapshot por envío (D9) y tarifa por
  tenant; el panel nunca recalcula el histórico.
- **[Zona horaria]** → todo en UTC; los cálculos de ventana se prueban con turnos
  creados en `America/Argentina/Buenos_Aires` para detectar off-by-one.
- **[PII en logs o seeds]** → R14: solo pacientes sintéticos; el número no se
  persiste en la fila de envío y la auditoría guarda hash.
- **[SMTP no configurado en dev]** → `SMTP_URL` vacío; se agrega Mailhog al compose
  de desarrollo para poder ejercitar el fallback sin cuentas reales.
- **[Webhook expuesto a abuso]** → firma HMAC obligatoria; el rate limit fino queda
  para C-13, que es el dueño del hardening de superficies públicas.
- **[Polling de 15 min]** → aceptado: a 300–3.000 mensajes/mes el costo de latencia
  es irrelevante frente a la simplicidad de un solo estado auditable.

## Open Questions

- **Turno creado dentro de la ventana** (por ejemplo, a 12 h del inicio): D10 define
  que la ventana cuyo instante de envío ya pasó se omite, porque enviar un
  recordatorio "T-24h" a 12 h contradice la configuración del tenant. No está
  definido por la KB; debe registrarse como **PA-09** en
  `knowledge-base/10_preguntas_abiertas.md` y validarse con el dueño del producto
  antes de implementar. Este change no edita la KB para no mezclar alcance.
- **Categoría de plantilla y tarifa real de Meta** varía por país y tipo de mensaje;
  `config.whatsapp_costo_centavos` es una estimación por tenant hasta que exista
  facturación real del proveedor.
- **Texto legal del opt-in y de los mensajes** (PA-07) sigue pendiente; el motor no
  cambia si el texto cambia.
