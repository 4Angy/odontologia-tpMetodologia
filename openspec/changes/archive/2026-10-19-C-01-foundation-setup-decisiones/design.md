# Design — C-01 `foundation-setup-decisiones`

> Decisiones tomadas en `discovery/explore-c01-foundation-setup-decisiones.md` (explore con `visual-explore-options`). Selección del usuario: Eje 1 → A, Eje 2 → A, Eje 3 → A, Eje 4 → A, M1 → Postgres 16 real en dev y CI.
> Ver `proposal.md` para la motivación. Este documento explica **cómo** se implementa.

## Context

Estado real del repo verificado el 2026-10-19 (no supuesto):

- Existe un slice funcional archivado (`2026-10-06-cancelar-turno-liberar-horario`): `backend/app/main.py`, `backend/app/core/security.py`, `backend/app/deps.py`, `backend/app/modules/agenda/` (model, repositorio, service, router, schemas, seed y 4 archivos de test) y `frontend/src/features/agenda/`. Sus tests corren sobre `sqlite:///:memory:` con `StaticPool`.
- La migración `0001_cancelacion_turno` ya creó `tenant` (mínima), `turno` (mínima) y `config` (mínima). `alembic/env.py` ya usa `create_engine` **sincrónico** con `postgresql+psycopg://` por defecto, pero `requirements.txt` **no declara ningún driver de base de datos**.
- Falta todo lo que C-01 debe aportar: `core/config.py`, `core/errors.py`, `core/logging.py`, `GET /health`, `app/worker/`, `docker-compose.yml`, `.env.example` (raíz/backend/frontend), `.github/workflows/`, `docs/adr/`, y en frontend `src/main.tsx`, `src/App.tsx`, `src/shared/`, `src/pages/`, router, `react-router-dom` y los scripts `dev`/`build`.
- `CHANGES.md` asigna `tenant`/`usuario`/`config` a C-02 ("Migración 001") y `turno` a C-07 ("Migración 006"): las migraciones ya existentes se adelantan a sus changes dueños.
- `core/security.py` tiene un secreto de fallback hardcodeado (`"dev-secret-cambiar"`), incompatible con la regla de no secretos en el repo.

Restricciones que modelan el diseño: multi-tenancy row-level (R1/R2), DTOs Pydantic v2 con `extra='forbid'` (R3/R4), datetimes UTC con timezone (R7), errores con `code` RN-XX mostrable en español-AR (R9/RN-GL-01), migraciones reversibles (R6), TDD estricto (R11), datos sintéticos (R14), y el filtro de calidad de la KB: **costo operativo bajo** (DD-03).

## Goals / Non-Goals

**Goals:**

- Dejar el andamiaje mínimo pero **real**: settings por env con fail-fast, health checks, logging, contrato de error transversal, compose de un solo deploy, CI en verde con jobs paralelos.
- Cerrar por escrito las tres decisiones que bloquean el Sprint 1 (ADR-001, ADR-002, ADR-003), cada una con owner y criterio de aplicación, sin implementarlas: eso corresponde a C-09, C-11 y C-05.
- Reconciliar el esquema real del repo con el plan de `CHANGES.md` **sin tirar código ni tests ya escritos**, y dejar la numeración de migraciones 003-012 intacta.
- Dejar la base de datos real (Postgres 16) en dev y CI, para que R1, índices compuestos, CHECK constraints y el RLS futuro de C-13 se validen contra el motor de producción.

**Non-Goals:**

- No se implementa ningún dominio: no hay pacientes, agenda, caja, seña ni notificaciones. Los módulos `pacientes/`, `cobros/`, `notificaciones/`, `tenancy/` se crean **vacíos** (placeholder + `__init__.py`), los llena C-02/C-04/C-06/C-09/C-11.
- No se implementa el envío de WhatsApp (C-09), ni el modelo `cobros/` (C-11), ni la tabla `evolucion` (C-05): este change solo **documenta** esos contratos.
- No se implementa auth completa, refresh rotation ni RBAC (C-03); `core/security.py` queda como está, salvo por el fallback del secreto.
- No se migra a async SQLAlchemy: ver Decisión 5.
- No se implementa RLS de Postgres (endurecimiento post-v1, DD-04).
- No se escribe el frontend de negocio: solo el shell mínimo (router + api client + un placeholder de página) que C-03/C-04/C-07 van a poblar.

## Decisions

### 1. ADR-001 — WhatsApp v1 = `official` (Cloud API de Meta), un solo adaptador

La KB ya resolvió la *forma* de la decisión: `WHATSAPP_PROVIDER=official|gateway` está en la tabla de env vars y `02_descripcion_general.md` dice "API oficial Cloud API **o** gateway artesanal — POR DECIDIR". La interfaz `notificaciones/` es idéntica en ambos casos, así que lo que se decide es **qué se implementa en v1 y cuál es el default**.

Se implementa **un único adaptador**, `OfficialWhatsAppClient`, detrás de la interfaz `WhatsAppClient`; `WHATSAPP_PROVIDER=official` es el default. El valor `gateway` sobrevive en el enum, documentado como camino de v2, **sin implementar en v1**.

```text
[ Worker C-09 ] --> ( WhatsAppClient ) --> ( OfficialWhatsAppClient ) --> [ Meta Cloud API ] --> [ Paciente ]
                                            |
                                            +-- plantillas preaprobadas + webhooks de estado
                                            +-- costo por conversacion --> [ panel de consumo C-09 ]
```

- **Rationale:** la apuesta C.4-1 del análisis competitivo ("WhatsApp primero, honesto": API oficial + costos transparentes + plantillas + opt-in + fallback + panel de consumo) y el MVP de D.3 ("recordatorios y confirmaciones por WhatsApp (API oficial) + email fallback") ya apuntan a la API oficial. El filtro de la KB es costo operativo bajo, y el costo real del gateway no es $0: es riesgo de baneo del número, entregabilidad no garantizada y **ausencia de estado de entrega confiable**, lo que volvería el panel de consumo de C-09 un estimado en vez de un dato. El costo del camino oficial es dinero, que se puede medir y mostrar —que es justamente el diferenciador que C-09 tiene que vender.
- **Alternativa descartada — `gateway` artesanal** (Evolution API / Baileys / whatsapp-web.js sobre número propio): costo ~$0 por mensaje y arranque inmediato, pero baneo, sin plantillas oficiales, sin webhooks de estado y en contradicción directa con C.4-1/D.3. `CHANGES.md` ya anticipaba el daño ("si PA-01 elige gateway artesanal, riesgo de baneo que C-09 debe absorber").
- **Alternativa descartada — ambos adaptadores en v1** (`official` como default + `gateway` como failover): duplica la superficie de un change que ya es ALTO (C-09), y el failover solo tiene sentido si el proveedor oficial es una causa real de caída, no un modo de operación.
- **Consecuencias concretas en C-01:** (a) `.env.example` documenta `WHATSAPP_PROVIDER=official` con su default; (b) `docs/adr/ADR-001-whatsapp-provider.md` fija proveedor, tabla de costos por tipo de mensaje, entregabilidad, riesgo de baneo y fallback a email, más el **runbook de onboarding por tenant** (crear WABA, registrar y aprobar plantillas) porque la aprobación de plantillas es proceso de Meta, no de código; (c) la tabla de costos por mensaje que C-09 necesita para el panel de consumo queda escrita ahora, aunque el panel llegue en C-09.

### 2. ADR-002 — "Facturación" v1 = caja manual, sin comprobante

DD-02 ya decidió "caja manual sin AFIP/ARCA en v1" y RN-CO-01 lo codifica ("la UI lo declara para no defraudar expectativas"). Lo que faltaba era **operacionalizarlo** para C-11, que hoy no sabe si debe crear un comprobante.

En v1: `cobros/` = `cobro` + `cierre_caja`. **No** existe tabla `recibo` ni campo `numero_comprobante`. El cierre es diario e inmutable (RN-CO-04) y el saldo siempre derivado (RN-CO-05). La UI de caja declara el alcance.

```text
[ Caja ] --> [ cobros + saldos + deudas + cierre del dia ] --> ( sin comprobante )
                                                 |
                                    [ UI: "caja manual, sin comprobantes fiscales" ]
```

- **Rationale:** C-11 ya es CRITICO (dinero: inmutabilidad del cierre + saldo derivado) y no necesita un +2-4h de numeración correlativa y generación de PDF para cumplir el scope. IN-01/SU-03 dicen que el riesgo real no es técnico sino de expectativa: se mitiga declarándolo, no construyéndolo a medias.
- **Alternativa descartada — caja manual + recibo interno numerado (no fiscal)**: cubre la expectativa mínima de "tengo un papel" sin meterse con ARCA y mantiene el diferencial de transparencia negativa (Dentatools). Se descarta **para v1** porque suma alcance a un change CRITICO y porque abre la peor confusión posible (el dueño leería "recibo" como "factura"). **Revisión:** si en las demos de D.1 la objeción "necesito un comprobante" aparece de forma repetida, el recibo interno entra como change de v2 con su propio ADR, no como parche de C-01/C-11.
- **Consecuencias concretas en C-01:** `docs/adr/ADR-002-alcance-facturacion.md` con el modelo exacto de `cobros/` que C-11 implementa, y la redacción de la declaración de UI que C-11 y C-13 van a mostrar. `knowledge-base/06_funcionalidades.md` (US-006/US-008) se actualiza para que C-11 no lo reinterprete.

### 3. ADR-003 — Contrato formal de migrabilidad FDI (cierre verificable de R1)

DD-01 decidió salir de v1 sin odontograma; el riesgo R1 ("los 15 competidores lo tienen como núcleo") está abierto y el propio `CHANGES.md` exige que C-01 deje el plan de migración "por escrito". Un plan en prosa no es una garantía: lo que hace falta es un **contrato de campos** que C-05 pueda cumplir y verificar.

`evolucion` todavía no existe (la crea C-05), así que C-01 no puede migrar datos: puede **fijar la forma** que los datos van a tener. El contrato:

| Campo de `evolucion` v1 | Tipo | Rol en la proyección a FDI v2 |
|---|---|---|
| `id`, `tenant_id`, `paciente_id`, `profesional_id` | id / FK | se conservan |
| `fecha` (timestamptz UTC) | timestamptz | se conserva |
| `motivo` | texto | texto libre de la pieza |
| `detalle` | texto | texto libre de la pieza |
| `pieza_fdi_slot` | enum nullable (`dent` \| `face` \| `tooth` \| `zone`) + `pieza_fdi_numero` nullable | **ancla de la pieza** (notación FDI) |
| `odontograma_ref` | id nullable | referencia al registro FDI v2 |
| `firma_simple` + `firmado_at` | bool + timestamptz | alcance legal declarado (NO firma digital, Ley 25.506) |

- **Rationale:** con el contrato escrito, C-05 puede añadir un criterio de aceptación verificable —"toda `evolucion` creada bajo el contrato v1 es proyectable a odontograma FDI v2 sin pérdida de información relevante" + un test de proyección— y R1 queda **mitigado por escrito y testeado**, que es exactamente lo que el scope de C-01 pide. Los campos `pieza_fdi_slot`/`pieza_fdi_numero` son la diferencia entre "guardar texto libre" y "poder mapear a FDI sin adivinar".
- **Alternativa descartada — nota narrativa** ("en v2 se migra a FDI"): cero costo en C-01, pero deja la deuda abierta y la descubrible tarde, cuando el odontograma v2 ya tenga datos de v1 que no encajan. Eso es el riesgo R1 sin mitigating.
- **Consecuencias concretas en C-01:** `docs/adr/ADR-003-migrabilidad-fdi.md` con la tabla de arriba, la regla de proyección y el criterio de aceptación que C-05 hereda.

### 4. Esquema: se respeta `0001_cancelacion_turno`; C-02 = `002`, C-07 = ALTER de `turno`

`0001_cancelacion_turno` ya es la base real del esquema. No se retira ni se renumera: se la adopta y se ajusta el plan en dos puntos.

```text
0001 (existente)  -> tenant(min) + turno(min) + config(min)
002  C-02         -> usuario + ALTER tenant + ALTER config
003  C-04         -> paciente + optin
004  C-05         -> evolucion + adjunto + presupuesto + presupuesto_item
005  C-06         -> profesional + prestacion + bloqueo
006' C-07         -> ALTER turno (token_publico, origen, senia_id)
007  C-08         -> turno.token_publico unique + expiracion
008  C-09         -> notificacion_envio + plantilla
009  C-10         -> lista_espera
010  C-11         -> cobro + cierre_caja
011  C-12         -> senia (+ turno.senia_id)
012  C-13         -> auditoria
```

- **Rationale:** el slice ya escrito (4 archivos de test backend + 1 frontend) sobrevive intacto, `turno` ya nace con `tenant_id NOT NULL` (R1 alineado desde el día 0) y con `AwareDateTime` (R7). La numeración del plan **casi no se mueve**: el slot `002` estaba libre, y solo cambian dos líneas de `CHANGES.md` (C-02 y C-07). El costo de re-alinear (retirar `0001`, devolver `turno` a su change dueño) es alto: había que mover código validado y dejar el change archivado sin implementación viva.
- **Consecuencias concretas en C-01:** (a) `CHANGES.md` se actualiza — C-02 pasa a "Migración 002: crea `usuario`, extiende `tenant` y `config`" y C-07 a "Migración 006: extiende `turno`"; (b) `turno` **no nace en su change dueño** (deuda documentada: C-07 extiende, no crea); (c) el placeholder `turno.senia_pendiente_definicion` sobrevive hasta C-12, que lo lee y reemplaza por `senia_id` — queda anotado en el ADR-002/ADR-003 y en `CHANGES.md` para que nadie lo tome por deuda de C-01; (d) `alembic/env.py` debe apuntar al `Base` de **todos** los módulos, no solo `agenda`.
- **Alternativa descartada — realinear el repo al plan** (retirar `0001_cancelacion_turno`, que `tenant`/`usuario`/`config` los cree C-02 y `turno` C-07): deja `CHANGES.md` literal y cada change dueño de sus migraciones, a costa de tirar código y tests ya escritos y de dejar sin implementación el change archivado.

### 5. SQLAlchemy sincrónico + psycopg 3 (no async)

El repo ya está comprometido con el driver sincrónico: `alembic/env.py` usa `create_engine` con `postgresql+psycopg://` y `seed_demo.py` usa `create_engine` + `sessionmaker`; los 4 archivos de test usan `sqlite:///:memory:` con `StaticPool`. El único que dice otra cosa es el ejemplo de `DATABASE_URL` en `08_arquitectura_propuesta.md` (`postgresql+asyncpg://`).

Se mantiene **sincrónico** (SQLAlchemy 2.0 + psycopg 3) y se actualiza el ejemplo de la KB.

- **Rationale:** cero reescritura del slice y sus tests; un solo modelo mental (sync) para C-02 y su `BaseRepository[T]`/`UnitOfWork`; psycopg 3 es rápido; a la escala de un consultorio chico el threadpool de FastAPI alcanza de sobra. Migrar a async ahora significa reescribir `deps.py`, `repository.py`, los fixtures de test y `alembic/env.py`, más `pytest-asyncio`, dentro de un change de 4-6h que además tiene que fundar settings, health, CI, compose y tres ADR. El filtro de la KB es costo operativo bajo, y el costo de esa reescritura es alto e inmediato, con beneficio diferido e hipotético.
- **Alternativa descartada — async SQLAlchemy + asyncpg**: mejor concurrencia en el worker de C-09 y en los webhooks. Se difiere con un **trigger de re-evaluación explícito**: C-13 revisa el perfil con datos reales (picos de turnos, uso de webhooks) y, si el sync no alcanza, la migración a async se hace como change propio con su plan de migración de sesiones.
- **Consecuencia concreta en C-01:** `DATABASE_URL` pasa a `postgresql+psycopg://odontologia:odontologia@db:5432/odontologia` en la KB, en `.env.example` y en el compose. `requirements.txt` agrega `psycopg[binary]`.

### 6. Settings: `pydantic-settings`, 14 variables, fail-fast en boot

Se crea `backend/app/core/config.py` con una clase `Settings` (frozen, `BaseSettings`) que lee **14** variables canónicas (las 14 filas de la tabla `§Variables de entorno` de `08_arquitectura_propuesta.md`; `CHANGES.md` decía 13 y se corrige) más dos variables operativas: `APP_ENV` (`dev` | `test` | `prod`) y `LOG_LEVEL`.

`APP_ENV` es **operativa, no canónica**, pero es obligatoria: sin ella, un despliegue de producción que la olvide caería silenciosamente en modo `dev` (con secreto de firma efímero y sin fail-fast). Declararla evita toda una clase de "en prod funciona pero no como creías".

`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ACCESS_MIN`, `JWT_REFRESH_DAYS`, `TENANT_DEFAULT_TZ`, `WHATSAPP_PROVIDER`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`, `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `SMTP_URL`, `PUBLIC_BASE_URL`, `SEED_DEMO`.

`Settings` se instancia **una vez** al boot y se inyecta; los valores sensibles son `SecretStr` y nunca se loguean.

- **Rationale:** `pydantic-settings` da validación de tipos, lectura de `.env` opcional y un error claro al boot si falta o es inválida una variable, en vez de un fallo difuso a mitad de una request. `JWT_SECRET` es la única que **no** tiene default: si falta, la app no arranca (salvo en `dev`/`test`, donde se permite un fallback con warning visible). Esto elimina el `"dev-secret-cambiar"` hardcodeado de `core/security.py`, que hoy contradice la regla de no secretos en el repo.
- **Alternativa descartada — dataclass + `os.getenv` por uso**: menos dependencias, pero sin validación ni coerción de tipos, y cada call site repite el parseo.

### 7. Health: `/health` (liveness) y `/health/ready` (readiness)

- `GET /health` → `200 {"status": "ok", "service": "...", "version": "..."}`. **No toca la base de datos ni Redis**: es liveness, sirve para el healthcheck del contenedor y para "la applevantó".
- `GET /ready` → `200` solo si la conexión a Postgres y a Redis responden; si no, `503` con el componente que falla. Es readiness, sirve para el balanceador y para que el compose no enrute tráfico a una app sin base.

Ambos son públicos y sin auth (no exponen datos de negocio ni de tenant).

- **Rationale:** el scope de C-01 pide `GET /health`; dividir liveness de readiness evita el error clásico de un healthcheck que reinicia el contenedor porque Postgres todavía no está listo, y da a C-13 (hardening) un punto de enganche para los healthchecks reales.
- **Alternativa descartada — un solo `/health` que chequee todo**: reinicios espurios en el arranque y ambigüedad sobre qué significa "ok".
- **Nota de rutas**: se implementan como `GET /health` y `GET /health/ready` (prefijo común) para no colisionar con rutas raíz en el futuro.

### 8. Sobre de error: `AppError` + handler único

Se formaliza en `backend/app/core/errors.py` la clase `AppError(code, message, action=None, status_code=400)` y un handler único en `main.py` que serializa **siempre** `{code, message, action?}` (R9/RN-GL-01, español-AR mostrable). `code` es un RN-XX cuando la regla de negocio lo causa (`RN-AG-01`, `RN-CO-01`, `RN-AU-01`…) y un código genérico documentado (`RN-GL-00`) para errores que no mapean a una regla.

El `HTTPException` con `detail` dict que ya usa `main.py` **se mantiene** (compatibilidad con el slice archivado) pero se documenta como forma interna; la forma pública es la que fija `AppError`.

- **Rationale:** R9 exige `code` trazable; con una clase única el contrato no depende de que cada router recuerde la forma del dict, y los tests pueden afirmar la forma del cuerpo sin conocer el router. `action` conserva el placeholder de reprogramar que el spec `agenda/cancelacion-turno` ya define.
- **Alternativa descartada — seguir con `HTTPException(detail={...})` en cada router**: menos indirección, pero el contrato queda implícito y se erosiona con el primer endpoint nuevo.

### 9. CI: dos jobs en paralelo + Postgres 16 y Redis 7 como services

`.github/workflows/ci.yml` con dos jobs sin dependencia entre sí:

- **job `backend`**: Python 3.12, `pip install -r backend/requirements.txt`, services `postgres:16` y `redis:7`, y en orden: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` (prueba R6 de reversibilidad contra Postgres real) → `pytest`.
- **job `frontend`**: Node 20, `npm ci`, `tsc --noEmit` (R10) → `vitest run`.

Ambos jobs reportan por separado; el workflow no tiene matriz todavía (no hay versiones multiple que probar). Secrets: **ninguno** — el job `backend` no usa secrets de GitHub: la conexión a Postgres 16 y Redis 7 se hace con las credenciales **de los propios service containers del job**, declaradas como variables de entorno del runner (`DATABASE_URL`, `REDIS_URL`, `TEST_DATABASE_URL`) y con un `JWT_SECRET` de CI que no es un secreto real (sólo cumple la regla de arranque de `APP_ENV=test`). El job `frontend` tampoco requiere secrets.

- **Rationale:** el scope pide "jobs paralelos backend/frontend", y correr el ciclo completo de migraciones en CI es la única forma de que R6 sea una garantía y no una intención. Los jobs no se bloquean entre sí, así que el tiempo total es el del job más lento.
- **Alternativa descartada — un solo job secuencial**: menos YAML, pero el feedback de frontend espera al de backend.

### 10. Tests contra Postgres 16 real; SQLite solo para unitarios sin DB

`backend/tests/conftest.py` (nuevo) provee la sesión de tests: lee `TEST_DATABASE_URL` (default `postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia_test`), crea un **schema aislado por corrida**, aplica `Base.metadata.create_all` y lo dropea al terminar. Si `TEST_DATABASE_URL` empieza con `sqlite://`, usa `sqlite:///:memory:` con `StaticPool` (el modo actual), para que los unitarios sin DB sigan siendo rápidos y portables.

- **Rationale:** la decisión M1 (Postgres 16 real en dev y CI) es la que hace que R1 (índices compuestos, unicidad por tenant), los CHECK constraints y el RLS futuro de C-13 se validen contra el motor real; correr siempre en SQLite dejaría diferencias sin detectar (tipos, `timestamptz`, stricter de Postgres, casing de columnas). El modo SQLite se conserva como **atajo**, no como default de CI.
- **Alternativa descartada — correr toda la suite en SQLite**: rápido, pero el CI no verifica nada del motor de producción y las diferencias aparecen en C-02/C-04 con el schema ya cargado.

### 11. Compose: `api` + `worker` + `db` + `redis`, un solo deploy

`docker-compose.yml` con cuatro servicios: `db` (`postgres:16`, volumen nombrado, healthcheck `pg_isready`), `redis` (`redis:7` con `--appendonly yes`, healthcheck `redis-cli ping`), `api` (build multi-stage desde `backend/`, `depends_on` con `condition: service_healthy`), `worker` (misma imagen, comando distinto, sobre `app/worker/`).

Los dos servicios de aplicación toman sus variables de un `.env` de la raíz; `docker-compose.yml` **no** contiene secretos (solo `${VAR}` con defaults de dev sin secreto real, y `JWT_SECRET` requerido).

- **Rationale:** DD-03 ("Compose = un deploy") y el scope de C-01 (api + worker + postgres 16 + redis 7). AOF en Redis es lo que exige el patrón "Cola + scheduler" de `08_arquitectura_propuesta.md` (la cola de C-09 no puede perder recordatorios en un reinicio).
- **Alternativa descartada — levantar Postgres/Redis solo con Dockerfiles y no compose**: dos comandos manuales por cada dev y por CI; contradice "un solo deploy".

### 12. Frontend: router v6 + api client con `code` RN-XX

Se agrega `react-router-dom` v6 y se crea: `src/main.tsx` (bootstrap), `src/App.tsx` (shell con rutas placeholder `/agenda`, `/pacientes`, `/caja`, `/config` — las mismas que define C-03), `src/shared/api/client.ts` (wrapper de `fetch` con `VITE_API_BASE_URL`, timeouts, y **traducción del sobre `{code, message, action?}` a un error tipado** que las pantallas puedan mostrar en español-AR), `src/shared/ui/` (componentes base) y `src/pages/`. Se agregan los scripts `dev`, `build`, `preview` a `package.json`.

- **Rationale:** el scope pide "router, api client base"; el manejo centralizado del `code` RN-XX evita que cada pantalla reinterprete el contrato de error (que C-07 ya ejercita con `RN-AG-01`).
- **Alternativa descartada — axios**: agrega una dependencia y un interceptor propio cuando `fetch` con un wrapper de ~40 líneas alcanza para este tamaño.

### 13. Worker: esqueleto sin jobs

`backend/app/worker/` con `main.py` que abre la conexión a Redis, registra logging y entra en un loop de scheduler **sin jobs registrados** (log explícito "no jobs registrados" en cada tick). El servicio `worker` del compose lo ejecuta.

- **Rationale:** `CHANGES.md` pide `docker-compose (api + worker + postgres 16 + redis 7)` y C-09 es su dueño. Un worker sin jobs es el mínimo honesto que permite el compose pedido sin anticipar el motor de notificaciones (C-09, governance ALTO, RN-PA-03 anti-spam, reintentos, fallback).
- **Alternativa descartada — no crear `worker/` hasta C-09**: el compose del scope de C-01 quedaría con un servicio inexistente, o C-01 tendría que tocar el compose dos veces.

### 14. Sin secretos en el repo y sin fallback silencioso

`JWT_SECRET` no tiene default fuera de `dev`/`test`; en `dev` el fallback genera uno **efímero por proceso** con warning en el log (no un string fijo en el código), de modo que reiniciar el proceso invalida los tokens anteriores en lugar de mantener un secreto conocido y público. `core/security.py` deja de usar `"dev-secret-cambiar"`. `.env.example` lleva solo placeholders y `docs/` explica cómo generarlo (`openssl rand -hex 32`).

- **Rationale:** la regla de no secretos en el repo y el runbook de rotación de C-13. Un secreto fijo hardcodeado es un secreto público, aunque sea "solo para dev".
- **Alternativa descartada — mantener el fallback fijo con warning**: es exactamente el estado actual y es el que el change tiene que cerrar.

## Risks / Trade-offs

- [Riesgo] La migración `0001` crea tablas **antes** que sus changes dueños, así que `turno` nace sin `token_publico`/`origen`/`senia_id` y `tenant` sin `slug` → Mitigación: C-01 documenta la tabla de propiedad de cada tabla (C-02 extiende `tenant`/`config`, C-07 extiende `turno`) y actualiza `CHANGES.md`; las columnas agregadas en C-08/C-12 son `ALTER` sobre tablas existentes, no `CREATE`.
- [Riesgo] El placeholder `turno.senia_pendiente_definicion` puede quedar huérfano si C-12 no lo retira → Mitigación: queda anotado en `CHANGES.md` (C-12) y en el ADR-002 como deuda con owner explícito; C-12 lo reemplaza por `senia_id`.
- [Riesgo] C-07 hereda una tabla `turno` que no creó, y su test de aislamiento tiene que seguir funcionando sobre el esquema ampliado → Mitigación: C-07 abre con una tarea de "reconciliación" que verifica que el esquema de `turno` cumple el contrato de C-07 antes de agregar endpoints.
- [Riesgo] Correr los tests contra Postgres 16 en CI puede sacar a la luz diferencias del slice actual (tipos, `timestamptz`, `CHECK`) que hoy pasan en SQLite → Mitigación: es el objetivo de la decisión M1; si aparece algo, se corrige en C-01 (es andamiaje, no dominio) y no se degrada a "SQLite en CI".
- [Riesgo] `official` implica costo por mensaje y un proceso de aprobación de plantillas que es de Meta, no del equipo → Mitigación: el ADR-001 trae la tabla de costos y el runbook de onboarding por tenant; el panel de consumo de C-09 es la respuesta de producto; si el costo resulta insostenible para el consultorio chico, la reversión es cambiar el default del enum a `gateway` (que queda soportado por la interfaz desde el día 1).
- [Riesgo] "Caja manual sin comprobante" puede defraudar si el dueño espera factura (IN-01/SU-03) → Mitigación: declaración explícita en la UI (C-11), en el onboarding (C-13) y en la landing; si la objeción se repite en demos, el recibo interno entra como change de v2 con su propio ADR (Decisión 2).
- [Trade-off] Se mantiene SQLAlchemy sincrónico → Menos concurrencia potencial en el worker de C-09 y en webhooks; a cambio, cero reescritura y un solo modelo mental. Trigger de re-evaluación explícito: C-13 con datos reales.
- [Trade-off] Se implementa un solo adaptador de WhatsApp → sin failover ante caída del proveedor oficial; a cambio, el fallback de la KB es email (RN-PA-04) y no un segundo proveedor con doble mantenimiento.
- [Trade-off] CI con dos jobs y services real → más tiempo de CPU que SQLite en memoria; a cambio, el CI verifica contra el motor de producción, que es donde se rompen las diferencias de esquema.

## Migration Plan

C-01 **no mueve datos**: es andamiaje + documentación. El único artefacto de esquema que toca es la ampliación del alcance de migraciones futuras (no se ejecuta ninguna migración nueva en este change).

1. **Repositorio**: se crean `backend/app/core/{config,errors,logging}.py`, `backend/app/worker/`, `backend/tests/conftest.py`, `frontend/src/{main.tsx,App.tsx,shared/,pages/}`, `docker-compose.yml`, `.env.example` (x3), `.github/workflows/ci.yml`, `docs/adr/` (ADR-001..003 + README), y los `__init__.py` de los módulos vacíos.
2. **Documentación**: se actualizan `CHANGES.md` (C-01 entregables, C-02/C-07 numeración de migraciones, "14 vars"), `knowledge-base/08` (esquema de `DATABASE_URL` a psycopg + nota de settings), `knowledge-base/09` (PA-01 y PA-02 pasan a resueltas, con owner) y `knowledge-base/10` (PA-01/PA-02 se marcan resueltas por ADR-001/ADR-002).
3. **Sin downtime / rollback**: al no haber migración de datos ni cambios de contrato de API, el rollback es revertir el commit y redeploy. La única incompatibilidad posible es `core/security.py` dejando de aceptar el secreto fijo: si algo externo dependía de `JWT_SECRET="dev-secret-cambiar"`, se pasa a leerlo de `.env` (cambio de una línea, documentado en el runbook).
4. **Post-despliegue**: `docker compose up -d` levanta los cuatro servicios; `GET /health` y `GET /health/ready` responden; `alembic upgrade head` deja el esquema en `0001` sin cambios respecto de hoy.
5. **Verificación de reversibilidad**: el ciclo `upgrade head → downgrade -1 → upgrade head` se ejecuta en CI contra Postgres 16 (R6) y queda replicable en local con `make migrate-check` (o el comando equivalente documentado en el README).

## Open Questions

- **PA-04** (antelación por prestación vs. una global): afecta `config` en C-06, no este change. Diferible.
- **PA-05** (política de devolución de seña y medios): afecta C-12. Diferible.
- **PA-06** (TTL y prioridad de lista de espera): afecta C-10. Diferible.
- **PA-08** (antelación mínima de reserva pública y timeout de pago pendiente): afecta C-08. Diferible.
- **SU-01** (¿WhatsApp decide la compra?): se valida con 5 entrevistas antes del Sprint 2; no bloquea C-01, pero su resultado puede obligar a cambiar el default del enum en C-09 (la interfaz queda lista para eso).
- **Costo real de `official` por consultorio**: la tabla de costos del ADR-001 es la mejor estimación disponible; se recalcula con datos de consumo reales cuando C-09 tenga el panel. No cambia el diseño de C-01.
- **Umbral de migración a SQLAlchemy async**: se evalúa en C-13 con el perfil real de uso. No bloquea este change ni C-02..C-12.
