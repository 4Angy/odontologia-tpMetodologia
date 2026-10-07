# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup-decisiones
  └── C-02 tenancy-core-models
        └── C-03 auth-rbac-multirole                          ← desbloquea TODO lo demás
              │
              ├── C-04 pacientes-crud-optin                   [Agente A]
              │     └── C-05 ficha-clinica-presupuestos       [Agente A]
              │
              ├── C-06 catalogo-agenda-base                   [Agente B] ← paralelo con C-04
              │     └── C-07 turnos-agenda-interna            [Agente B] ← + C-04
              │           ├── C-08 reserva-publica-tokens     [Agente B]
              │           │     ├── C-09 notificaciones-whatsapp     [Agente C] ← + C-04
              │           │     │     └── C-10 lista-espera-automatica  [Agente C]
              │           │     └── C-12 senias-mercadopago          [Agente A] ← + C-11
              │           └── C-11 cobros-caja-manual                [Agente A] ← + C-04
              │
              └── C-13 shell-transparencia-hardening ← + C-05 + C-10 + C-12 (cierre, solo al final)
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 (solo)

GATE 1: C-01 ✓
  → C-02 (solo)

GATE 2: C-02 ✓
  → C-03 (solo)

GATE 3: C-03 ✓                     ← PRIMER FORK (2 paralelos)
  → C-04 pacientes-crud-optin      [Agente A]
  → C-06 catalogo-agenda-base       [Agente B]

GATE 4: C-04 + C-06 ✓
  → C-05 ficha-clinica-presupuestos [Agente A]
  → C-07 turnos-agenda-interna      [Agente B]

GATE 5: C-07 ✓                     ← FORK (reserva pública vs caja en paralelo)
  → C-08 reserva-publica-tokens     [Agente B]
  → C-11 cobros-caja-manual         [Agente A]

GATE 6: C-08 ✓                     ← FORK (notificaciones vs señas)
  → C-09 notificaciones-whatsapp    [Agente C]
  → C-12 senias-mercadopago         [Agente A — si C-11 ✓]

GATE 7: C-09 ✓
  → C-10 lista-espera-automatica    [Agente C]

GATE 8: C-05 + C-10 + C-12 ✓
  → C-13 (solo, cierre y hardening)
```

### Camino crítico (9 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-07 → C-08 → C-09 → C-10 → C-13
```

> Nota: C-06 corre en paralelo con C-04 y debe cerrarse antes de C-07 (mismo nivel, no alarga el plazo).
> Rama co-crítica comercial: `C-11 → C-12*` — sin seña por MP no existe el diferenciador "compromiso real"
> (DD-05); si la seña se considera indispensable para el lanzamiento, el camino crítico real es de 10 changes
> sustituyendo C-10 por C-11 → C-12 antes de C-13.

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)      │ Agente B (Backend Aux)         │ Agente C (Frontend)
─────┼──────────────────────────────┼────────────────────────────────┼─────────────────────────
  1  │ C-01 foundation-setup        │         —                      │         —
  2  │ C-02 tenancy-core-models     │         —                      │         —
  3  │ C-03 auth-rbac-multirole     │         —                      │         —
  4  │ C-04 pacientes-crud-optin    │ C-06 catalogo-agenda-base      │         —
  5  │ C-05 ficha-clinica           │ C-07 turnos-agenda-interna     │         —
  6  │ C-11 cobros-caja-manual      │ C-08 reserva-publica-tokens    │ C-09 notificaciones (*)
  7  │ C-12 senias-mercadopago      │         —                      │ C-10 lista-espera
  8  │         —                    │         —                      │ C-13 hardening-final (**)
```

> (*) C-09 es backend worker + panel de consumo; el Agente C lo toma en el paso 6 porque A y B están
> ocupados con C-11/C-08. (**) C-13 lo ejecuta quien libere primero (idealmente C con contexto de C-09/C-10).

---

## FASE 0 — Cimientos y decisiones bloqueantes

> El primer change resuelve PA-01 y PA-02: sin esas dos decisiones el diseño del Sprint 1 no puede arrancar.

### [C-01] `foundation-setup-decisiones`
- **Estado**: `[ ]` pendiente
- **Scope**: Scaffolding completo del monorepo + infraestructura base + decisiones bloqueantes documentadas
  - Estructura de directorios según `08_arquitectura_propuesta.md`: `backend/app/{core,modules/{agenda,pacientes,cobros,notificaciones,tenancy},worker,alembic,tests}`, `frontend/src/{features,shared,pages}`, `docker-compose.yml` (api + worker + postgres 16 + redis 7)
  - `backend/`: FastAPI app mínima con `GET /health`, settings por env vars (13 vars de `08` §Variables de entorno), logger, manejo de errores con `code` trazable a RN-XX (RN-GL-01)
  - `frontend/`: Vite + React 18 + TypeScript 5 scaffolding, router, api client base
  - `.env.example` en cada sub-proyecto, sin secretos hardcodeados; GitHub Actions CI con jobs paralelos backend/frontend
  - ADR-001 (resuelve **PA-01**): proveedor WhatsApp v1 — `official` (Cloud API) vs `gateway` artesanal, con tabla de costos por mensaje, entregabilidad, riesgo de baneo y fallback; fija `WHATSAPP_PROVIDER`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`
  - ADR-002 (resuelve **PA-02**): alcance exacto de "facturación" v1 — solo caja manual (RN-CO-01) o recibo interno no fiscal numerado; fija el modelo de `cobros/` para C-11
  - Registro R1-mitigation: plan de migración v1→v2 garantizada hacia odontograma FDI (qué campos de `evolucion` serán migrables, ver DD-01)
  - Tests: health check, carga de settings, CI en verde
- **Dependencias**: ninguna
- **Governance**: ALTO (las decisiones PA-01/PA-02 condicionan todo el Sprint 1; el scaffolding solo sería BAJO)
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios + §Variables de entorno
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/10_preguntas_abiertas.md` §PA-01 + §PA-02 (las dos decisiones a cerrar aquí)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01 (R1) + §DD-03 (stack)
  - `discovery/analisis-competitivo.md` §C.3-2 (WhatsApp) + §C.4-2 (seña MP)
- **Riesgos**: R1 (salir sin odontograma cuando los 15 competidores lo tienen) — se mitiga dejando el plan de migración v1→v2 por escrito en este change; si PA-01 elige gateway artesanal, riesgo de baneo que C-09 debe absorber con reintentos + fallback email.

---

## FASE 1 — Identidad y pacientes

> C-04 y C-06 corren en paralelo tras C-03. C-04 alimenta a C-05, C-07, C-09 y C-11 (paciente + opt-in son prerrequisito de turnos, notificaciones y cobros).

### [C-02] `tenancy-core-models`
- **Estado**: `[ ]` pendiente
- **Scope**: Modelos base multi-tenant + migraciones iniciales + seed mínimo
  - Modelos: `Tenant` (slug kebab-case único global, tz default `America/Argentina/Buenos_Aires`), `Usuario` (email único por tenant, `roles` array enum, `activo`), `Config` (antelacion_hs default 24, seña, plantillas)
  - `TenantMixin` con `tenant_id NOT NULL + FK`; unicidades y búsquedas siempre compuestas con `tenant_id` (RN-AU-01)
  - `AuditMixin` (`created_at`, `updated_at`, `deleted_at`), `BaseRepository[T]`, `UnitOfWork`
  - Middleware de tenant obligatorio: sin `tenant_id` del JWT → 403 (RN-AU-01); paginación cursor/limit base
  - Migración 001: tablas `tenant`, `usuario`, `config`; índices `(tenant_id, email)`, `slug`
  - Seed mínimo: 1 tenant demo (`slug: demo`) + 3 usuarios demo (uno por rol y uno con los 3 roles)
  - Tests: aislamiento multi-tenant (un tenant no ve datos de otro), unicidad compuesta, seed idempotente
- **Dependencias**: C-01
- **Governance**: CRITICO (todo el dominio referencia estos modelos; un bug de filtro expone datos cruzados — DD-04)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §tenant + §usuario + §Seed data inicial
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (Row-level multi-tenancy, Repository, UoW)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-04 (row-level) + §DD-06 (roles acumulables)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-01 + §RN-GL-02
- **Riesgos**: aislamiento roto por olvidar `tenant_id` en una query (mitigación: middleware + tests de aislamiento obligatorios en cada change posterior); RLS Postgres queda como endurecimiento post-v1, no día 1.

### [C-03] `auth-rbac-multirole`
- **Estado**: `[ ]` pendiente
- **Scope**: Autenticación JWT con RBAC acumulable + shell mínima del frontend (US-011)
  - `POST /auth/login` (email + password; 401 genérico sin revelar existencia; 403 si usuario inactivo), `POST /auth/refresh` (rotación con blacklist del anterior, reuse → revocación de familia RN-AU-02), `POST /auth/logout`, `GET /me`, `POST /auth/password-reset` (token 1h), `POST /users/invite` + `GET /users` (solo `dueno`)
  - JWT: access 15 min + refresh 7 días; claims `sub`, `tenant_id`, `roles`, `email`, `jti`, `type`, `iat`, `exp`; refresh en cookie HttpOnly (secure, samesite=lax); rate limiting 5/60s por IP+email en login
  - `PermissionContext`: `require_role()`, permiso efectivo = unión de roles (RN-AU-04); matriz RBAC de `03_actores_y_roles.md` aplicada como dependencias por router
  - Frontend: login page, auth/tenant context, App shell + routing base (`/agenda`, `/pacientes`, `/caja`, `/config`), derivación de permisos por unión de roles (incluye caso "todo en una persona", Flujo 4)
  - Tests: login ok/expirado/rate-limit, refresh rotation + reuse revoca familia, RBAC por rol, acumulable 3-roles-1-persona
- **Dependencias**: C-02
- **Governance**: CRITICO (auth + tenancy sostienen todo; desbloquea TODO lo demás)
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos + nota 3-roles-1-persona
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Auth multi-rol
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-02 + §RN-AU-04
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
- **Riesgos**: SU-02 (3-roles-1-persona genera caos de permisos/auditoría inútil) — mitigación: la auditoría registra rol activo por acción (DD-06) y test de usabilidad con 2 consultorios unipersonales antes de crear un rol "encargado".

### [C-04] `pacientes-crud-optin`
- **Estado**: `[ ]` pendiente
- **Scope**: Ficha base del paciente + opt-ins + importación/exportación (base de US-009, US-010 completo)
  - Modelos: `Paciente` (teléfono E.164, dni/email opcionales, `saldo` derivado no editable), `OptIn` (canal whatsapp/email, estado); validación: teléfono requerido si opt-in WhatsApp activo (RN-PA)
  - Endpoints: `CRUD /pacientes` (búsqueda por apellido/teléfono/dni con índices compuestos), `GET/PUT /pacientes/:id/optins`, `POST /pacientes/import-csv` (reporte ok/duplicadas/fallidas), `GET /export/:recurso.csv` (pacientes, turnos, cobros — RN-GL-04 anti lock-in)
  - Regla RN-PA-02: cambio de número invalida tokens/pendientes asociados al anterior
  - Frontend: lista + detalle + alta de paciente (< 30s de carga), gestión de opt-in visible, pantalla de importación con reporte
  - Migración 003: tablas `paciente`, `optin`; índices `(tenant_id, apellido)`, `(tenant_id, telefono)`, `(tenant_id, dni)`
  - Tests: CRUD + aislamiento, E.164 inválido rechaza opt-in, import CSV con duplicados, export incluye todo lo propio
- **Dependencias**: C-03
- **Governance**: MEDIO (datos de salud Ley 25.326: opt-in + minimización; sin pagos ni auth)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §paciente + §notificacion_envio / optin
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PA-01 + §RN-PA-02 + §RN-GL-04
  - `knowledge-base/06_funcionalidades.md` §US-009 (CA-1) + §US-010
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad (Datos salud, Ley 25.326)
- **Riesgos**: PA-07 (adecuación legal fina de opt-in/DPA queda para lanzamiento con abogado) — este change deja textos de opt-in parametrizables, no quemados; riesgo de importar base sucia (mitigación: reporte fila por fila, nunca falla silenciosa).

### [C-05] `ficha-clinica-presupuestos`
- **Estado**: `[ ]` pendiente
- **Scope**: HCE mínima + adjuntos + presupuestos simples (resto de US-009)
  - Modelos: `Evolucion` (motivo, detalle, `firma_simple` bool + timestamp con alcance legal declarado — NO firma digital Ley 25.506), `Adjunto` (RX/fotos, límite 10 MB configurable), `Presupuesto` + `PresupuestoItem` (alimenta saldo/deuda, RN-CO-05)
  - Endpoints: `GET /pacientes/:id/evoluciones` (timeline desc), `POST /pacientes/:id/evoluciones`, `POST /pacientes/:id/adjuntos` (validación tipo/tamaño), `CRUD /pacientes/:id/presupuestos`
  - Frontend: ficha única con timeline de evoluciones + adjuntos + presupuestos/saldo (Flujo 3, pasos 1-3)
  - Migración 004: tablas `evolucion`, `adjunto`, `presupuesto`, `presupuesto_item`; índice `(tenant_id, paciente_id, fecha desc)`
  - Tests: evolución firmada registra auditoría, adjunto > límite rechaza con mensaje claro, presupuesto alimenta saldo derivado
- **Dependencias**: C-04
- **Governance**: MEDIO (HCE mínima con implicancia legal declarada; sin pagos)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §evolucion
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Atención y registro clínico mínimo
  - `knowledge-base/06_funcionalidades.md` §US-009 (CA-2, CA-3)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01 (R1: qué queda deliberadamente fuera)
- **Riesgos**: **R1 directo** — la ficha sin odontograma puede resultar eliminatoria en demos (gatillo D.3: si lo exigen, adelantar odontograma a v1); mitigación de este change: campos de `evolucion` diseñados migrables a odontograma FDI v2 (registrado en C-01) + adjuntos que ya cubren RX/fotos como paliativo.

---

## FASE 2 — Agenda núcleo

> C-06 corre en paralelo con C-04. C-07 exige ambos (turno referencia paciente + profesional/prestación).

### [C-06] `catalogo-agenda-base`
- **Estado**: `[ ]` pendiente
- **Scope**: Catálogo de agenda + configuración del tenant (base de US-001, US-004)
  - Modelos: `Profesional` (`usuario_id` nullable — puede no tener login; `color_agenda`, `activo`), `Prestacion` (`duracion_min`, `precio_ref` nullable para seña/presupuesto, `activa`), `Bloqueo` (profesional/sillón + rango), extensión de `Config` (antelacion_hs default 24, antelación mínima de reserva default 2h, recordatorios T-48h/T-24h)
  - Endpoints: `CRUD /profesionales`, `CRUD /prestaciones`, `CRUD /bloqueos`, `GET/PUT /config` (solo `dueno`, RN-AG-02; rige para turnos futuros)
  - Cálculo de huecos reales: duración por prestación + bloqueos + antelación mínima (servicio reutilizable por C-07 y C-08)
  - Frontend: pantallas de profesionales/prestaciones/bloqueos + config del tenant (regla 24h editable)
  - Migración 005: tablas `profesional`, `prestacion`, `bloqueo`; seed de prestaciones (limpieza 30', consulta 20', arreglo 45', conducto 60' — duraciones editables)
  - Tests: huecos excluyen bloqueos, config solo editable por dueño, cambio no retroactivo
- **Dependencias**: C-03
- **Governance**: MEDIO (config con efecto en reglas de negocio; sin dinero ni datos clínicos)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §profesional / prestacion + §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-02 + §RN-AG-06
  - `knowledge-base/06_funcionalidades.md` §US-001 (CA-1) + §US-004
  - `knowledge-base/10_preguntas_abiertas.md` §PA-04 (regla 24h por prestación) + §PA-08 (defaults 2h/30 min)
- **Riesgos**: PA-04/PA-08 son defaults propuestos sin validar (24h igual para primera visita con seña que para control; 2h/30 min) — mitigación: todos configurables por tenant desde este change, nunca constantes quemadas.

### [C-07] `turnos-agenda-interna`
- **Estado**: `[ ]` pendiente
- **Scope**: Agenda interna completa con anti-solape y regla 24h (US-001 + US-004)
  - Modelo: `Turno` (paciente, profesional, prestación nullable, `inicio`/`fin` timestamptz, `estado`: pendiente_confirmacion|confirmado|presente|ausente|cancelado|reprogramado, `origen`, `token_publico` unique, `senia_id` nullable)
  - Endpoints: `CRUD /turnos`, `POST /turnos/:id/confirmar|cancelar|reprogramar|presente|ausente`, `GET /agenda/dia|semana`; validación de solape por profesional en app + índice (RN-AG-03); colisión → 409 con 3 huecos alternativos (RN-AG-03); sobreturno explícito flag + motivo, nunca silencioso (RN-AG-04)
  - Cancelación: valida antelación contra config (RN-AG-01/02); fuera de término → error `code: RN-AG-01` + oferta de reprogramar; reprogramar arrastra seña (RN-AG-05, ejecutado en C-12)
  - Idempotency keys en creación de turnos (doble-clic no duplica)
  - Frontend: vista día/semana multi-profesional, alta de turno con huecos propuestos, gestión del día (presente/ausente), cancelación con mensaje de error mostrable en español-AR (RN-GL-01)
  - Migración 006: tabla `turno`; índices `(tenant_id, profesional_id, inicio)`, `(tenant_id, inicio)`
  - Tests: solape rechaza + sugiere 3 huecos, sobreturno exige motivo y permiso, cancelación <24h devuelve `RN-AG-01`, idempotencia
- **Dependencias**: C-04, C-06
- **Governance**: ALTO (máquina de estados del turno + errores trazables RN-XX que ven los usuarios)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §turno
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-01 + §RN-AG-03 + §RN-AG-04 + §RN-AG-05 + §RN-GL-01
  - `knowledge-base/06_funcionalidades.md` §US-001 + §US-004
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 (cancelación) + §Flujo 3 paso 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (Idempotency keys)
- **Riesgos**: condición de carrera en doble reserva del mismo hueco (mitigación: validación en app + índice + idempotency key; test de concurrencia); métrica de éxito "agenda diaria < 5 min" depende de esta UX — validar con recepcionista real en prototipo.

### [C-08] `reserva-publica-tokens`
- **Estado**: `[ ]` pendiente
- **Scope**: Reserva pública 24/7 por link + acciones del paciente sin login (US-002)
  - Rutas públicas (rate-limit + sin JWT): `GET /r/:tenantSlug` (página pública con disponibilidad real), `POST /public/reservar` (crea turno `pendiente_confirmacion` RN-AG-07, respeta bloqueos/duración/antelación RN-AG-06), `POST /public/turnos/:token/confirmar|cancelar|reprogramar` (token único por turno con expiración default 72h post-turno, RN-AU-03)
  - Opt-in WhatsApp capturado en la reserva (RN-PA-01); si la prestación exige seña → crea preferencia MP y devuelve `checkout_url` (contrato definido aquí, cobrado en C-12)
  - Pago no acreditado en 30 min → job libera el hueco y avisa (default configurable, Flujo 1)
  - Frontend: página pública liviana `/r/:slug` (fuera del shell autenticado), botones de WhatsApp con token
  - Migración 007: columnas `turno.token_publico` (unique) + expiración; índice `token_publico`
  - Tests: reserva respeta bloqueos, token expirado rechaza, rate-limit en rutas públicas, turno nace `pendiente_confirmacion`
- **Dependencias**: C-07
- **Governance**: ALTO (superficie pública sin auth: abuso/spam/seguridad; tokens con expiración)
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Reserva pública con seña
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-06 + §RN-AG-07 + §RN-AU-03
  - `knowledge-base/06_funcionalidades.md` §US-002
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad (rate-limit, token con expiración)
- **Riesgos**: abuso de la ruta pública (reservas falsas que bloquean el sillón) — mitigación: rate-limit + captcha + expiración + liberación a 30 min; RN-AU-03 72h y timeout 30 min son supuestos (PA-08) — parametrizables.

---

## FASE 3 — Anti-ausentismo

> El corazón del valor pagable (dolor: ausentismo = plata perdida). C-09 depende de C-07 + C-08; C-10 depende de C-09.

### [C-09] `notificaciones-whatsapp-worker`
- **Estado**: `[ ]` pendiente
- **Scope**: Motor de notificaciones WhatsApp + fallback email + panel de consumo (US-003 + US-012 CA-1)
  - Modelos: `NotificacionEnvio` (paciente, turno nullable, canal, plantilla, `estado`: encolada|enviada|entregada|fallida, `costo_estimado`, `provider_msg_id`), `Plantilla` (confirmación, recordatorio, cancelación, lista de espera, seña — español-AR)
  - Worker Redis: scheduler cada 15 min selecciona turnos en ventana T-48h/T-24h sin envío y con opt-in; máximo 1 mensaje por ventana/turno (RN-PA-03 anti-spam); confirmación con un toque por token → turno `confirmado` (RN-PA-01: sin opt-in no hay envíos, se registra el motivo)
  - Resiliencia (RN-GL-03): proveedor caído → reintento exponencial 3 intentos → fallback email si hay (RN-PA-04) → `fallida` visible con botón reintentar; cola persistente Redis AOF; el turno igual queda confirmado aunque falle el envío
  - Endpoints: `POST /notificaciones/test`, `GET /notificaciones/consumo` (mensajes + costo estimado por período), `POST /webhooks/whatsapp` (estados + inbound idempotente por `provider_msg_id`)
  - Proveedor concreto según ADR-001 de C-01 (`WHATSAPP_PROVIDER` official|gateway)
  - Frontend: panel de consumo/costo WhatsApp visible para el dueño (US-012 CA-1)
  - Migración 008: tablas `notificacion_envio`, `plantilla`; índices `(tenant_id, created_at)`, `(tenant_id, estado)`
  - Tests: 1 mensaje por ventana, sin opt-in no envía, reintento + fallback, webhook duplicado idempotente, panel muestra costos
- **Dependencias**: C-07, C-08 (usa C-04 opt-ins; corre en paralelo con C-11)
- **Governance**: ALTO (integración externa falible + costos por mensaje + anti-spam legal)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Recordatorios programados (worker)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PA-01 + §RN-PA-03 + §RN-PA-04 + §RN-GL-03
  - `knowledge-base/06_funcionalidades.md` §US-003 + §US-012 (CA-1)
  - `knowledge-base/04_modelo_de_datos.md` §notificacion_envio / optin
  - `knowledge-base/10_preguntas_abiertas.md` §PA-01 (ADR-001 de C-01 es input directo)
- **Riesgos**: **PA-01** (si C-01 eligió gateway artesanal: baneo/costo oculto) + SU-01 (sobre-invertir en WhatsApp si no es lo que decide la compra — validar con 5 entrevistas antes del Sprint 2); costo operativo (prioridad de calidad): plantillas y ventanas configurables para contener el gasto por tenant.

### [C-10] `lista-espera-automatica`
- **Estado**: `[ ]` pendiente
- **Scope**: Lista de espera con oferta automática por WhatsApp (US-005)
  - Modelo: `ListaEspera` (paciente, profesional nullable = cualquiera, prestación nullable, prioridad, `estado`: activa|ofrecida|convertida|vencida)
  - Endpoints: `POST /lista-espera` (alta), `GET /lista-espera` (cola auditable), acciones aceptar/declinar por token (reutiliza mecanismo C-08)
  - Motor: al liberarse un hueco compatible → primer `activa` elegible pasa a `ofrecida` + WhatsApp con TTL default 2h; acepta → turno asignado (arrastra seña si corresponde, RN-AG-05); declina/vence → siguiente; sin opt-in → se salta con motivo registrado (RN-PA-01)
  - Frontend: vista de cola para recepción (estados auditables), botón de oferta manual
  - Migración 009: tabla `lista_espera`; índice `(tenant_id, estado, prioridad)`
  - Tests: oferta al primero elegible, TTL vence → pasa al siguiente, aceptar asigna turno y sale de la lista, sin opt-in se salta
- **Dependencias**: C-09 (usa el motor de envíos; corre en paralelo con C-12)
- **Governance**: MEDIO (máquina de estados con TTL; sin dinero directo)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-005
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 (pasos 4-5)
  - `knowledge-base/04_modelo_de_datos.md` §lista_espera
  - `knowledge-base/10_preguntas_abiertas.md` §PA-06 (TTL 2h y FIFO son supuestos a validar)
- **Riesgos**: PA-06 (TTL 2h y orden FIFO sin validar — ¿score de ausentismo?) — mitigación: TTL y criterio de prioridad configurables; riesgo de spam si el motor ofrece en bucle (mitigación: un `ofrecida` por hueco a la vez + auditoría de transiciones).

---

## FASE 4 — Cobros y caja

> C-11 corre en paralelo con C-08/C-09. C-12 cierra la promesa "reserva = compromiso real" (DD-05). Alcance fijado por ADR-002 de C-01.

### [C-11] `cobros-caja-manual`
- **Estado**: `[ ]` pendiente
- **Scope**: Caja manual + saldos/deudas + cierre diario inmutable (US-006 + US-008)
  - Modelos: `Cobro` (paciente, turno nullable, monto, medio efectivo/transferencia/mp/otro, concepto, usuario que cobró, fecha), `CierreCaja` (fecha, totales por medio, observaciones, usuario; inmutable — solo nota de ajuste auditada RN-CO-04)
  - Saldo/deuda siempre derivado (cobros − presupuestos/señas aplicadas), ningún endpoint lo edita directo (RN-CO-05)
  - Endpoints: `CRUD /cobros` (alta < 30s), `GET /deudas` (ordenada por antigüedad/monto), `POST /caja/cierre-dia`, `POST /caja/ajuste` (nota auditada), `GET /caja/cierre-dia` (conciliación por medio)
  - UI honesta (RN-CO-01 + ADR-002): la pantalla declara que v1 es caja manual sin comprobantes fiscales
  - Frontend: pantalla de caja (cobro rápido, deudas, cierre del día con totales por medio)
  - Migración 010: tablas `cobro`, `cierre_caja`; índices `(tenant_id, fecha)`, `(tenant_id, paciente_id)`
  - Tests: saldo derivado automático, cierre inmutable (edición directa rechaza), ajuste deja auditoría, deudas ordenadas
- **Dependencias**: C-04, C-07
- **Governance**: CRITICO (dinero: inmutabilidad del cierre + saldo derivado; error aquí = pérdida de confianza del dueño)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §senia / cobro / cierre_caja
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CO-01 + §RN-CO-04 + §RN-CO-05 + §RN-GL-02
  - `knowledge-base/06_funcionalidades.md` §US-006 + §US-008
  - `knowledge-base/10_preguntas_abiertas.md` §PA-02 (ADR-002 de C-01 fija el alcance: ¿recibo interno o solo caja?)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-02 + §SU-03 (caja-manual-no-defrauda)
- **Riesgos**: **PA-02/SU-03** (si el dueño esperaba factura electrónica, v1 defrauda aunque cumpla spec — IN-01) — mitigación: declaración honesta en UI + landing desde el día 1 y validación en demos; IN-02 contenida: este change NO implementa checkout general, solo caja manual.

### [C-12] `senias-mercadopago`
- **Estado**: `[ ]` pendiente
- **Scope**: Seña por Mercado Pago con arrastre ante reprogramación (US-007)
  - Modelo: `Senia` (turno, paciente, monto, `mp_preference_id`, `mp_payment_id` nullable, `estado`: pendiente|acreditada|devuelta|aplicada)
  - Flujo: seña configurable por tenant/prestación (monto, requerida/opcional RN-CO-02); reserva pública genera preferencia MP → `checkout_url`; `POST /webhooks/mercadopago` acredita (idempotencia por `mp_payment_id`) → turno confirmado; pago no acreditado en 30 min → se libera (contrato con C-08)
  - Reprogramar arrastra la seña (RN-AG-05; si el nuevo turno no requiere seña → saldo a favor); devolución parametrizable `no_devuelve|devuelve_50|devuelve_100` según antelación (RN-CO-03, default: en término → saldo a favor, fuera de término → se pierde)
  - Webhook-first con retries MP; ninguna caída de MP bloquea el flujo local (RN-GL-03)
  - Frontend: config de seña por prestación, estado de seña en el turno, aviso de arrastre al reprogramar
  - Migración 011: tabla `senia` (+ `turno.senia_id`)
  - Tests: webhook duplicado idempotente, reprogramar arrastra (no cobra dos veces), devolución según política, sin seña acreditada no confirma (cuando es requerida)
- **Dependencias**: C-08, C-11
- **Governance**: CRITICO (dinero real + webhooks externos + idempotencia de pagos)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 (pasos 3-4) + §Flujo 2 (paso 2: destino de la seña)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CO-02 + §RN-CO-03 + §RN-AG-05
  - `knowledge-base/06_funcionalidades.md` §US-007
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (Webhook-first, Idempotency keys) + §Variables de entorno (MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET)
  - `knowledge-base/10_preguntas_abiertas.md` §PA-05 (política de devolución y medios)
- **Riesgos**: PA-05 (¿solo saldo a favor o devolución MP real en v1?) — default saldo a favor, documentado; fricción de onboarding (cada consultorio necesita cuenta MP — DD-05: guía paso a paso obligatoria); credenciales MP por tenant (rotación manual documentada en runbook, C-13).

---

## FASE 5 — Cierre y lanzamiento

> Solo arranca con C-05 + C-10 + C-12 archivados. Es el gate de salida a producción.

### [C-13] `shell-transparencia-hardening`
- **Estado**: `[ ]` pendiente
- **Scope**: Transparencia radical + auditoría + hardening de lanzamiento (US-012 + salida a producción)
  - Transparencia (US-012, diferenciador): sección "qué no hace (aún)" con roadmap honesto (incluye odontograma v2+ y FE ARCA — gestiona R1/SU-03 en la UI), precio ARS del plan visible in-app (SU-04), panel de consumo WhatsApp por período (datos de C-09)
  - Auditoría (RN-GL-02): middleware que registra quién/cuándo/qué en toda mutación + vista consultable por el dueño (incluye rol activo por acción, DD-06); Migración 012: tabla `auditoria`
  - Hardening: rate-limit en todas las rutas públicas (C-08) + login (C-03), validación E.164/tamaños, backups Postgres diarios + cifrado en reposo del proveedor, rotación manual de secretos documentada (runbook v1), checklist de lanzamiento (métricas §01: ausentismo −30%, time-to-value < 24h, transparencia binaria)
  - Seed demo completo (tenant demo + agenda + pacientes + caja de ejemplo) y guía de onboarding en el día (alta + CSV + prueba sin tarjeta)
  - Tests: auditoría registra mutaciones, rate-limit bloquea abuso, seed demo levanta un tenant operable, checklist de lanzamiento en verde
- **Dependencias**: C-05, C-10, C-12
- **Governance**: ALTO (gate de producción: seguridad, auditoría y promesas públicas)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-012 + §Épica 6 (qué declarar como "no hace")
  - `knowledge-base/01_vision_y_objetivos.md` §Métricas de éxito + §Fuera de alcance
  - `knowledge-base/05_reglas_de_negocio.md` §RN-GL-02 + §RN-GL-04
  - `knowledge-base/09_decisiones_y_supuestos.md` §SU-04 (precio ARS vs tiers gratuitos) + §DD-01 (texto honesto sobre R1)
  - `discovery/analisis-competitivo.md` §C.2 (Dentatools/transparencia) + §D.3 (gatillos: posicionamiento antes del código)
- **Riesgos**: SU-04 (transparencia no compensa tiers gratuitos Gendu/Turnito/Doctocliq — mitigación: posicionamiento/precio definido antes del código, test A/B de landing); PA-07 (adecuación legal fina Leyes 25.326/26.529/25.506 con abogado antes del lanzamiento — este change la exige como checklist, no la sustituye).
