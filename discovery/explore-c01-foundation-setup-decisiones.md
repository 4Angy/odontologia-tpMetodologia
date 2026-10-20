# Explore: C-01 `foundation-setup-decisiones`

- Fecha: 2026-10-19
- Modo: `visual-explore-options` (thinking-partner, NO implementacion, NO codigo, NO design.md)
- Change: `C-01 foundation-setup-decisiones` (GATE 0, unico, sin dependencias)
- Governance declarado: **ALTO** (las decisiones PA-01/PA-02 condicionan todo el Sprint 1)
- Fuentes leidas: `CHANGES.md` (C-01, C-02, C-07, C-09, C-11, C-12), `knowledge-base/02_descripcion_general.md`, `05_reglas_de_negocio.md` (RN-CO-01..05), `08_arquitectura_propuesta.md` (estructura + env vars), `09_decisiones_y_supuestos.md` (DD-01..06, SU-01..04), `10_preguntas_abiertas.md` (PA-01, PA-02, IN-01), `discovery/analisis-competitivo.md` (C.3, C.4, D.3), `discovery/explore-cancelar-turnos.md`, `AGENTS.md` (R1-R14), y el estado real del repo (`backend/`, `frontend/`, `alembic/`).

---

## 0. DECISIONES TOMADAS (selección del usuario, 2026-10-19)

| Eje | Opción elegida | Consecuencia |
|-----|----------------|--------------|
| 1 — ADR-001 (PA-01) WhatsApp | **A — `official`** (Cloud API de Meta) | Un solo adaptador; `gateway` queda en el enum como v2, sin implementar. → DD-07 / ADR-001. Owner: C-09 |
| 2 — ADR-002 (PA-02) facturación | **A — solo caja manual**, sin comprobante | Sin tabla `recibo` ni `numero_comprobante`. Recibo interno → change de v2. → DD-02 (resolución final) / ADR-002. Owner: C-11 |
| 3 — Esquema y migraciones | **A — respetar `0001_cancelacion_turno`** | C-02 pasa a `002` (crea `usuario`, extiende `tenant`/`config`); C-07 pasa a extender `turno`. Numeración 003-012 intacta. → CHANGES.md actualizado |
| 4 — Migrabilidad FDI | **A — ADR-003 con contrato de campos** | Lista cerrada de campos de `evolucion` v1 migrables + criterio de aceptación y test de proyección para C-05. → ADR-003. Owner: C-05 |
| M1 — Base de datos | **Postgres 16 real en dev y CI** | SQLAlchemy 2.0 sincrónico + psycopg 3 (el repo ya usa `create_engine` síncrono); SQLite queda como atajo para unitarios sin DB. Trigger de re-evaluación a async: C-13 |

**Artefactos generados:** `openspec/changes/C-01-foundation-setup-decisiones/proposal.md` + `design.md` (2/4 artefactos del schema `spec-driven`). Faltan `specs/` y `tasks.md` (fase `/opsx:propose`).

**KB actualizada:** `09` (DD-01, DD-02, DD-07), `10` (PA-01/PA-02 marcadas resueltas), `08` (14 env vars, `postgresql+psycopg://`, nota de settings).

---

## 1. Que pide C-01 (checklist de aceptacion)

De `CHANGES.md`:

1. Estructura de directorios canonica (`backend/app/{core,modules/*,worker,alembic,tests}`, `frontend/src/{features,shared,pages}`).
2. `docker-compose.yml` (api + worker + postgres 16 + redis 7).
3. Backend: FastAPI minima con `GET /health`, settings por env vars, logger, errores con `code` trazable a RN-XX.
4. Frontend: Vite + React 18 + TS 5, router, api client base.
5. `.env.example` por sub-proyecto, sin secretos; GitHub Actions CI con jobs paralelos backend/frontend.
6. **ADR-001** (resuelve PA-01): proveedor WhatsApp v1.
7. **ADR-002** (resuelve PA-02): alcance exacto de "facturacion" v1.
8. **Registro R1-mitigation**: plan de migracion v1->v2 garantizada hacia odontograma FDI.
9. Tests: health check, carga de settings, CI en verde.

## 2. Estado real del repo (verificado, no supuesto)

Existe scaffolding parcial, heredado del change archivado `2026-10-06-cancelar-turno-liberar-horario`:

| Existe | Falta (scope de C-01) |
|--------|------------------------|
| `backend/app/main.py` (FastAPI + handler de errores dict `code/message`) | `GET /health`, `core/config.py`, `core/errors.py`, `core/logging.py` |
| `backend/app/core/security.py` (JWT minimo) | `app/worker/`, `modules/{pacientes,cobros,notificaciones,tenancy}` |
| `backend/app/deps.py` (sesion + reloj inyectables) | `docker-compose.yml` |
| `backend/alembic/versions/0001_cancelacion_turno.py` | `.env.example` (raiz, backend, frontend) |
| `backend/requirements.txt` (falta `asyncpg`/`psycopg`, `redis`, `pydantic-settings`) | `.github/workflows/` (CI) |
| `backend/alembic/env.py`, `alembic.ini` | `docs/adr/` (ADR-001, ADR-002) |
| `frontend/src/features/agenda/` (api + `CancelarTurno.tsx` + test) | `src/App.tsx`, `src/main.tsx`, `src/shared/`, `src/pages/`, router, api client base |
| `frontend/package.json` (react 18, vite 6, vitest) | scripts `dev`/`build`, `react-router-dom` |

**Colision de numeracion de migraciones (hallazgo critico):**

- La migracion `0001_cancelacion_turno` ya creo `tenant` (minima), `turno` (minima) y `config` (minima). Su propia docstring lo declara: *"seed de C-06/C-07"*.
- `CHANGES.md` asigna esas tablas a otros changes: `tenant`/`usuario`/`config` -> **C-02 "Migracion 001"**; `turno` -> **C-07 "Migracion 006"**.
- El slice trae una columna placeholder `senia_pendiente_definicion` que existe solo porque C-12 todavia no existe.
- El `explore` de cancelar-turnos (`discovery/explore-cancelar-turnos.md`) ya concluyo que la cancelacion **debe vivir en C-07**, no en un change aparte. El codigo esta adelantado a su change dueño.

**Restricciones duras que acotan las opciones:** R1/R2 (tenant siempre del JWT), R4 (`extra='forbid'`), R5 (centavos enteros), R6 (migraciones reversibles), R7 (timestamptz UTC), R9 (`code` RN-XX), R11 (TDD), R14 (datos sinteticos), y el filtro de calidad de la KB: **costo operativo bajo**.

---

## 3. Eje 1 - ADR-001 (PA-01): proveedor de WhatsApp v1

> Dato clave: la KB **ya resolvio la forma de la decision** (`WHATSAPP_PROVIDER=official|gateway` esta en la tabla de env vars, y `02` dice "API oficial Cloud API **o** gateway artesanal - POR DECIDIR"). La interfaz `notificaciones/` es la misma en ambos casos. Lo que sigue abierto es **que se implementa en v1**, **cual es el default**, y **que pasa si el default falla**.

### Opcion A: `official` (Cloud API de Meta) como unico camino de v1

* **Que es?:** Los mensajes salen por la API oficial de WhatsApp Business (Meta): plantillas preaprobadas y conversaciones iniciadas por el paciente.
* **Por que y como:** Se implementa UN adaptador, `OfficialWhatsAppClient`, detras de la interfaz `WhatsAppClient`; `WHATSAPP_PROVIDER=official`, `WHATSAPP_API_TOKEN` (token de la WABA) y `WHATSAPP_PHONE_ID` quedan como ya define la KB. El worker de C-09 consume la misma interfaz, asi que el proveedor no se filtra al dominio. El valor `gateway` sobrevive en el enum como camino de v2 documentado. Requiere un runbook de onboarding por tenant (crear WABA, registrar plantillas, aprobar plantillas) porque la aprobacion es proceso de Meta, no de codigo.
* **Trade-off:** Pro: entregabilidad y legitimidad (numero de empresa, sin baneo), plantillas y webhooks de estado oficiales, y encaja con la apuesta C.4-1 ("WhatsApp primero, honesto": API oficial + costos transparentes + opt-in + fallback + panel de consumo) y con D.3 ("Recordatorios y confirmaciones por WhatsApp (API oficial) + email fallback") / Contra: costo variable por mensaje (obliga al panel de consumo de C-09) + proceso de aprobacion de plantillas + onboarding por consultorio
* **Esquema:**
```text
[ Worker C-09 ] --> ( WhatsAppClient ) --> ( OfficialWhatsAppClient ) --> [ Meta Cloud API ] --> [ Paciente ]
                                            |
                                            +-- plantillas preaprobadas + webhooks de estado
                                            +-- costo por conversacion --> [ panel de consumo C-09 ]
```

### Opcion B: `gateway` artesanal (Evolution API / Baileys / whatsapp-web.js) sobre numero propio

* **Que es?:** Un servicio autoalojado que se loguea a una cuenta de WhatsApp y manda mensajes por HTTP, sin pasar por Meta.
* **Por que y como:** Se implementa `GatewayWhatsAppClient` detras de la misma interfaz; el token del gateway ocupa `WHATSAPP_API_TOKEN` y el numero el `WHATSAPP_PHONE_ID`. Ventajas practicas: costo ~$0 por mensaje, arranque inmediato, sin aprobacion de plantillas (mensajes libres). C-09 tiene que absorber el riesgo de baneo con reintentos + fallback email (lo dice CHANGES.md: *"si PA-01 elige gateway artesanal, riesgo de baneo que C-09 debe absorber"*), y el panel de consumo quedaria con **costo estimado, no real**.
* **Trade-off:** Pro: costo operativo ~$0 y setup inmediato (el filtro de "costo operativo bajo" de la KB) / Contra: riesgo de baneo del numero, entregabilidad no garantizada, sin plantillas oficiales ni estado de entrega confiable, y contradice la apuesta C.4-1 y D.3
* **Esquema:**
```text
[ Worker C-09 ] --> ( WhatsAppClient ) --> ( GatewayWhatsAppClient ) --> [ Gateway autoalojado ] --> [ Paciente ]
                                            |
                                            +-- costo ~$0, sin plantillas, sin webhooks de estado
                                            +-- riesgo de baneo --> [ reintentos + fallback email ]
```

## 4. Eje 2 - ADR-002 (PA-02): alcance exacto de "facturacion" v1

### Opcion A: solo caja manual (RN-CO-01 tal cual)

* **Que es?:** Se registran cobros, se ven saldos/deudas y se cierra el dia. No se emite ningun comprobante.
* **Por que y como:** Es lo que ya dicen RN-CO-01 y DD-02. En C-01 eso se traduce a una instruccion negativa explicita para C-11: **no** crear tabla `recibo` ni campo `numero_comprobante` en `cobro`; el modelo de `cobros/` queda en `cobro` + `cierre_caja` (RN-CO-04 cierre inmutable, RN-CO-05 saldo derivado). La UI de caja declara "v1 es caja manual, sin comprobantes fiscales" (DD-02: "la UI debe declararlo para no defraudar"). C-01 lo escribe en el ADR-002 y lo baja a `knowledge-base/06_funcionalidades.md` (US-006/US-008) para que C-11 no lo reinterprete.
* **Trade-off:** Pro: cero trabajo extra, riesgo fiscal cero, cierra IN-01 con honestidad / Contra: si el dueno esperaba un comprobante, la decepcion aparece en la demo (SU-03) -> hay que decirlo antes, en landing y onboarding, no despues
* **Esquema:**
```text
[ Caja ] --> [ cobros + saldos + deudas + cierre del dia ] --> ( sin comprobante )
                                                 |
                                    [ UI: "caja manual, sin comprobantes fiscales" ]
```

### Opcion B: caja manual + recibo interno numerado (no fiscal)

* **Que es?:** Cada cobro genera un recibo con numero correlativo por tenant, descargable en PDF, **sin valor fiscal** (no ARCA, sin CUIT, sin validez legal). Es "un papel de mi consultorio", no un comprobante fiscal.
* **Por que y como:** Agrega a `cobro` un `numero` correlativo (secuencia por tenant, control de concurrencia en Postgres) y la vista PDF (ReportLab/WeasyPrint) con la leyenda "sin valor fiscal"; la UI de caja ofrece "descargar recibo". Es la alternativa (b) que DD-02 considero y descarto. Impacto: +2-4h en C-11 (que ya es CRITICO) + R5 (centavos) + R6 + leyenda anti-confusion.
* **Trade-off:** Pro: cubre la expectativa minima de "tengo un papel" sin meterse con ARCA y sin perder el diferencial de transparencia negativa (Dentatools) / Contra: +alcance en C-11 y riesgo de que el dueno lo lea como factura (decepcion invertida) -> la leyenda del PDF tiene que ser explicita
* **Esquema:**
```text
[ Caja ] --> [ cobros + saldos + deudas + cierre del dia ] --> [ recibo interno numerado (PDF) ]
                                                 |
                                    [ leyenda: "sin valor fiscal" ] --> ( ARCA sigue fuera de v1 )
```

## 5. Eje 3 - Destino del slice de cancelacion y numeracion de migraciones

### Opcion A: respetar `0001` y ajustar el plan en dos puntos

* **Que es?:** La migracion `0001_cancelacion_turno` queda como la base real del esquema. C-02 crea `002` (tabla `usuario` + ALTER de `tenant` y `config`); C-07 hace ALTER de `turno` (agrega `token_publico`, `origen`, `senia_id`) en vez de crearla. El resto de la numeracion (003 C-04, 004 C-05, 005 C-06, 006->alter C-07, 007 C-08, 008 C-09, 009 C-10, 010 C-11, 011 C-12, 012 C-13) queda intacto.
* **Por que y como:** No se tira codigo ni tests: los 4 archivos de test backend y el test frontend de cancelacion siguen valiendo. `turno` ya nace con `tenant_id NOT NULL` (R1 alineado desde el dia 0) y con `AwareDateTime` (R7). C-01 ademas agrega la infraestructura real que falta: `core/config.py` (settings pydantic, 14 env vars), `core/errors.py` (`code` RN-XX), `core/logging.py`, `GET /health`, `docker-compose.yml`, `.env.example` x3, CI con jobs paralelos, `docs/adr/ADR-001` y `ADR-002`.
* **Trade-off:** Pro: cero trabajo tirado, tests ya escritos siguen valiendo, el esquema base ya tiene tenant / Contra: el esquema base queda partido entre dos changes y `turno` nace fuera de su change dueno (rompe "cada change trae sus migraciones"); `CHANGES.md` deja de coincidir con el repo en C-02 y C-07; queda el placeholder `senia_pendiente_definicion` hasta C-12
* **Esquema:**
```text
0001 (existente)  -> tenant(min) + turno(min) + config(min)
002  C-02         -> usuario + ALTER tenant + ALTER config
003  C-04         -> paciente + optin
005  C-06         -> profesional + prestacion + bloqueo
006' C-07         -> ALTER turno (token_publico, origen, senia_id)
...  C-08..C-13   -> 007..012 (sin cambios)
```

### Opcion B: alinear el repo al plan y devolver `turno` a C-07

* **Que es?:** `0001_cancelacion_turno` se retira del esquema base: `turno` pasa a crearse en C-07 (migracion 006, como dice el plan) y `tenant`/`usuario`/`config` las crea C-02 (migracion 001). El slice de cancelacion actual se conserva como codigo de referencia y se re-integra en C-07, que es donde su propio explore lo ubico.
* **Por que y como:** `CHANGES.md` queda literal (001 = C-02, 006 = C-07) y cada change es dueno de sus migraciones. Se elimina el placeholder `senia_pendiente_definicion` (en C-07 el campo real es `senia_id`, ligado a C-12). C-01 paga el costo de mover/retirar el codigo anticipado: el slice de cancelacion, sus tests y la carpeta `openspec/changes/archive/2026-10-06-...` quedan como referencia documentada (con su decision asentada en `CHANGES.md` y en el ADR), sin implementacion viva en el esquema.
* **Trade-off:** Pro: repo alineado con el roadmap, atomicidad de migraciones por change, sin placeholder / Contra: C-01 tiene que mover codigo ya escrito y validado (4 tests backend + 1 frontend) y el change archivado queda sin implementacion en el repo
* **Esquema:**
```text
001  C-02  -> tenant + usuario + config
002  (libre)
003  C-04  -> paciente + optin
005  C-06  -> profesional + prestacion + bloqueo
006  C-07  -> turno (+ cancelacion re-integrada)
...  C-08..C-13 -> 007..012 (sin cambios)
```

## 6. Eje 4 - Migrabilidad FDI: contrato formal o nota

### Opcion A: ADR-003 con contrato de campos migrables (cierre verificable de R1)

* **Que es?:** Un ADR-003 escrito que fija la lista cerrada de campos de `evolucion` v1 que se proyectan a piezas FDI v2, mas el criterio de aceptacion que C-05 tiene que cumplir.
* **Por que y como:** `evolucion` todavia no existe (la crea C-05), asi que C-01 no puede migrar datos: puede **fijar el contrato** de campos. Ej.: `evolucion` lleva `pieza_fdi_slot` nullable (`dent`/`face`/`tooth`/`zone` + numero FDI), `odontograma_ref` nullable, `firma_simple` + `firmado_at` (no firma digital, Ley 25.506), `motivo`, `detalle`, `fecha`, `profesional_id`. C-05 agrega a sus criterios de aceptacion: "toda `evolucion` creada con el contrato v1 es proyectable a FDI sin perdida" + test que lo verifique. Con eso R1 queda mitigado por escrito, como pide el scope de C-01.
* **Trade-off:** Pro: la garantia de migracion deja de ser una promesa y pasa a ser un criterio de aceptacion verificable de C-05 / Contra: 1-2h de trabajo en C-01 y una restriccion de diseno que C-05 tiene que respetar (si C-05 la ignora, la migracion v1->v2 se rompe en silencio)
* **Esquema:**
```text
[ ADR-003: contrato v1 -> FDI ] --> [ C-05: evolucion con campos migrables ] --> [ v2: odontograma FDI ]
                    |                                     |
                    +-- criterio de aceptacion + test de proyeccion sin perdida
```

### Opcion B: nota narrativa, sin contrato

* **Que es?:** C-01 deja escrito el plan de migracion como narrativa ("en v2 se migra a FDI"), sin fijar campos ni criterio verificable.
* **Por que y como:** Es lo que hoy dice `09_decisiones_y_supuestos.md` DD-01 ("odontograma y HC completa van a v2+") sin detalle. C-05 diseña `evolucion` como vea y la migracion se resuelve cuando exista el odontograma v2.
* **Trade-off:** Pro: cero costo en C-01, sin restriccion para C-05 / Contra: "migracion garantizada" queda sin garantia (es exactamente el riesgo R1 que C-01 deberia cerrar) y la deuda se descubre tarde, cuando el odontograma v2 ya tiene datos en v1
* **Esquema:**
```text
[ nota en C-01 ] --> [ C-05: evolucion libre ] --> [ v2: re-interpretar a FDI (deuda abierta) ]
```

---

## 7. Decisiones menores (una linea cada una, con default recomendado)

| # | Decision | Default recomendado | Costo de revertir |
|---|----------|----------------------|-------------------|
| M1 | Base de datos en dev/CI | **Postgres 16 en dev (compose) y CI (service container)**; SQLite solo como atajo para tests hermeticos unitarios, que es como esta escrito el codigo actual (`AwareDateTime` re-ancla a UTC en SQLite). Razon: R1, indices compuestos, CHECK y RLS futuro solo se validan en Postgres | Medio (reescribir el harness de tests) |
| M2 | Ubicacion de los ADR | `docs/adr/ADR-001-whatsapp-provider.md`, `ADR-002-alcance-facturacion.md`, `ADR-003-migrabilidad-fdi.md` + indice en `docs/adr/README.md` | Bajo |
| M3 | Cantidad de env vars | La KB lista **14** (incluye `JWT_ACCESS_MIN` y `JWT_REFRESH_DAYS` como dos), `CHANGES.md` dice "13 vars". C-01 debe fixar 14 y corregir el conteo en `CHANGES.md` | Bajo |
| M4 | Settings: pydantic-settings vs dataclass | `pydantic-settings` (validacion al boot, `.env` opcional, tipos) | Bajo |
| M5 | Worker en C-01 | Crear `backend/app/worker/` con el esqueleto + cola Redis, pero **sin jobs**: C-09 es su dueno. Hoy `docker-compose.yml` no puede levantar un worker sin esqueleto minimo | Bajo |
| M6 | Frontend: router | `react-router-dom` v6 (lazy) + `src/shared/api/client.ts` con interceptor de `code` RN-XX. Falta `react-router-dom` en `package.json` y faltan los scripts `dev`/`build` | Bajo |
| M7 | Secrets | `.env.example` solo con placeholders; `JWT_SECRET` con fallback **solo** en dev/test y warning en boot si se usa (hoy `core/security.py` tiene `"dev-secret-cambiar"` hardcodeado) | Bajo |

---

## 8. Recomendacion

1. **Eje 1 -> Opcion A (`official`)** con `gateway` documentado en el enum y sin implementarlo en v1. Es lo que ya dijeron la KB (`D.3`), el analisis competitivo (`C.4-1`) y el filtro de costo operativo bajo (un baneo de numero es costo operativo alto). El riesgo real de esta opcion es costo, y ese costo es justo el diferenciador que C.09 tiene que mostrar.
2. **Eje 2 -> Opcion A (solo caja manual)**. Es DD-02 y RN-CO-01 ya decididos; B agrega alcance a un change CRITICO (C-11) y abre la puerta a la confusion "recibo = factura". Si en las demos aparece la objecion, B entra como **change de v2**, no como parche de C-01.
3. **Eje 3 -> Opcion A (respetar `0001`)**. El costo de re-alinear es bajo y el de romper el codigo ya escrito es alto; ademas la numeracion (002 C-02, 003 C-04, ... 012 C-13) queda casi intacta. Se actualiza `CHANGES.md` para que C-02 "extienda" `tenant`/`config` y C-07 "extienda" `turno`.
4. **Eje 4 -> Opcion A (ADR-003 con contrato de campos)**. Es el unico camino en que "migracion v1->v2 garantizada" es algo que se puede testear y no una promesa.
5. Combinacion natural si se quiere cobertura sin costo: **A + A + A + A**, con `gateway` de WhatsApp y el recibo interno ambos **documentados como v2** en sus ADRrespectivos.

---

## 9. Preguntas abiertas para la pausa

1. Eje 1: **A (official)**, **B (gateway)**, o **A con gateway como failover documentado** (implementar el enum y ambos adaptadores en C-09)?
2. Eje 2: **A (solo caja)**, **B (caja + recibo interno PDF)**, o **A ahora y B como change de v2 documentado**?
3. Eje 3: **A (respetar `0001`)**, **B (alinear al plan y devolver `turno` a C-07)**?
4. Eje 4: **A (ADR-003 con contrato de campos)**, **B (nota narrativa)**?
5. M1: Postgres 16 real en dev y CI (recomendado), o SQLite en dev/CI?

**PAUSA OBLIGATORIA.** Sin seleccion explicita no se genera `design.md`, ni `proposal.md`, ni codigo. La seleccion define el alcance de `/opsx:propose C-01-foundation-setup-decisiones`.

---

## 10. Trazabilidad

- Decisiones que cierra C-01: PA-01 (ADR-001), PA-02 (ADR-002), IN-01, y R1 (mitigacion documentada).
- Decisiones de KB que NO se re-evaluan (ya cerradas): DD-01 (sin odontograma en v1), DD-02 (caja sin ARCA), DD-03 (FastAPI+React+Postgres+Redis+Docker), DD-04 (row-level), DD-05 (sena MP), DD-06 (roles acumulables).
- Hard rules que condicionan el diseno de C-01: R1/R2 (tenant del JWT), R4 (`extra='forbid'`), R5 (centavos), R6 (`downgrade` en toda migracion), R7 (timestamptz UTC), R9 (`code` RN-XX), R10 (TS estricto), R11 (TDD, 2 casos por comportamiento), R12 (sin commit sin pedido), R13 (gobernanza ALTO -> analisis antes de codear), R14 (datos sinteticos).
- Consumidores de las salidas de C-01: C-02 (env vars + settings + `002`), C-03 (JWT_SECRET, JWT_ACCESS_MIN, JWT_REFRESH_DAYS), C-06/C-07 (`006` alter, `config.antelacion_cancel_hs`), C-09 (WHATSAPP_*), C-11 (ADR-002 -> modelo `cobros/`), C-12 (MP_*), C-13 (env vars, RLS futuro, backups).
