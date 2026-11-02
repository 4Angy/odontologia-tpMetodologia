# Evidencia de las 6 pruebas de `visual-explore-options` (3 con skill / 3 baseline)

> **Procedencia de este archivo.** Recuperado el 2026-10-27 y copiado literal, sin editar, de:
> 
> - `~\Downloads\visual-explore-options\evals\evals.json` (prompts de los evals),
> - `ses_eb9f350c3ffe0HR38j682fmrMj` (prompts de los subagentes, extraídos del registro de la sesión),
> - `~\Downloads\visual-explore-options-workspace\iteration-1\<eval>\eval_metadata.json` (criterios),
> - `~\Downloads\visual-explore-options-workspace\iteration-1\<eval>\{with,without}_skill\outputs\output.md` (las 6 salidas),
> - `~\Downloads\visual-explore-options-workspace\iteration-1\benchmark.json` (corrección de cada criterio).
>
> Sesión `ses_eb9f350c3ffe0HR38j682fmrMj` («Cómo usar skill-creator»), 2026-10-16. Bloques entre ~~~~ = copia textual.

---

## 1. Resultado declarado en la sesión

~~~~
Iteración 1 completa — **with_skill 100% vs baseline 40% (+0.60)**.

Archivos:
- Skill: `Downloads\visual-explore-options\SKILL.md`
- Viewer: `Downloads\visual-explore-options-workspace\iteration-1\review.html` (abierto arriba)
- Benchmark: `...iteration-1\benchmark.json`

### Qué prueban los evals
1. UI turnos React+Tailwind
2. Persistencia citas FastAPI+PG
3. API pacientes móvil/web

Assertions (5): ≥2 opciones, `Qué es + Por qué/cómo + Trade-off`, ASCII en ```text, pausa obligatoria sin `design.md`, recomendación.

### Resultado
- **with_skill:** 15/15. Los 3 outputs siguen plantilla exacta, ASCII corto y terminan con:
  > `[PAUSA OBLIGATORIA] Indica qué opción deseas...`
- **baseline:** 6/15. Da 3-4 opciones con más profundidad (ej. `eval-1` con DDL + `EXCLUDE USING gist`, índices, tabla comparativa; `eval-0` con `?patientId=&date=`, SWR) pero sin formato uniforme, sin ASCII y sin pausa — sigue de largo a APIs/siguientes pasos.

### Trade-off detectado
Tu skill gana en estandarización y freno, pierde en profundidad técnica. El baseline es mejor arquitecto, peor en proceso SDD.

Para iteración 2 propongo:
- Mantener plantilla obligatoria, pero agregar `Detalle técnico (opcional, max 15 líneas)` para SQL/endpoints/componentes
- Permitir 2-3 opciones (no forzar exactamente 2)
- Mantener ASCII ≤10 líneas + pausa dura

Decime:
1. ¿Te gusta esa dirección o preferís simplicidad extrema actual?
2. ¿Algún output con_skill te pareció demasiado simple o mal?
3. ¿Quieres que aplique el cambio y relance iteración-2 con `--previous-workspace`?
~~~~

---

## 2. Los prompts de los 3 evals (`evals.json`)

~~~~json
{"evals": [{"expected_output": "Dos opciones UI comparadas con Que es, Por que/como, Trade-off, esquema ASCII 3 columnas o similar, y pausa obligatoria sin generar design.md", "files": [], "id": 0, "prompt": "Estamos en fase explore del change 'pantalla de gestion de turnos': necesitamos mostrar lista de pacientes y huecos disponibles. Stack actual React + Tailwind. Presenta opciones."}, {"expected_output": "Dos opciones backend/DB comparadas (ej SQL vs NoSQL o REST vs alternativa) con por-que/como concreto, esquema flujo ASCII y pausa obligatoria", "files": [], "id": 1, "prompt": "Estamos en fase explore del change 'persistencia de citas y pacientes': 10k citas/mes, consultas por fecha y paciente. Stack FastAPI + PostgreSQL existente pero abierto a alternativas. Presenta opciones."}, {"expected_output": "Dos opciones API/arquitectura comparadas con trade-offs, esquema ASCII y pausa obligatoria", "files": [], "id": 2, "prompt": "Estamos en fase explore del change 'API de pacientes para app movil y web': alta lectura, pocas escrituras, auth necesaria. Presenta opciones de diseno API."}], "skill_name": "visual-explore-options"}
~~~~

---

## 3. Los 6 prompts exactos lanzados (3 con skill, 3 baseline)

Registro de la herramienta `subagent`, mensaje `seq=86`. Texto literal de cada `prompt`:

### `eval0 with skill UI`

~~~~
Execute this task:
- Skill path: C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md
- Primero lee el archivo SKILL.md de esa ruta y sigue sus instrucciones al pie de la letra (plantilla exacta, al menos 2 opciones, esquema ASCII, pausa obligatoria, no generar design.md).
- Task: Estamos en fase explore del change 'pantalla de gestion de turnos': necesitamos mostrar lista de pacientes y huecos disponibles. Stack actual React + Tailwind. Presenta opciones.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-0-frontend-ui\with_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md (respuesta completa con plantilla). No hagas nada mas.
~~~~

### `eval0 baseline UI`

~~~~
Execute this task:
- NO uses ninguna skill, responde de forma normal como lo harias sin instrucciones extra.
- Task: Estamos en fase explore del change 'pantalla de gestion de turnos': necesitamos mostrar lista de pacientes y huecos disponibles. Stack actual React + Tailwind. Presenta opciones.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-0-frontend-ui\without_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md. No hagas nada mas.
~~~~

### `eval1 with skill DB`

~~~~
Execute this task:
- Skill path: C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md
- Primero lee el archivo SKILL.md de esa ruta y sigue sus instrucciones al pie de la letra (plantilla exacta, al menos 2 opciones, esquema ASCII, pausa obligatoria, no generar design.md).
- Task: Estamos en fase explore del change 'persistencia de citas y pacientes': 10k citas/mes, consultas por fecha y paciente. Stack FastAPI + PostgreSQL existente pero abierto a alternativas. Presenta opciones.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-1-backend-db\with_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md. No hagas nada mas.
~~~~

### `eval1 baseline DB`

~~~~
Execute this task:
- NO uses ninguna skill, responde de forma normal como lo harias sin instrucciones extra.
- Task: Estamos en fase explore del change 'persistencia de citas y pacientes': 10k citas/mes, consultas por fecha y paciente. Stack FastAPI + PostgreSQL existente pero abierto a alternativas. Presenta opciones.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-1-backend-db\without_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md. No hagas nada mas.
~~~~

### `eval2 with skill API`

~~~~
Execute this task:
- Skill path: C:\Users\Cara Palida\Downloads\visual-explore-options\SKILL.md
- Primero lee el archivo SKILL.md de esa ruta y sigue sus instrucciones al pie de la letra (plantilla exacta, al menos 2 opciones, esquema ASCII, pausa obligatoria, no generar design.md).
- Task: Estamos en fase explore del change 'API de pacientes para app movil y web': alta lectura, pocas escrituras, auth necesaria. Presenta opciones de diseno API.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-2-api-arch\with_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md. No hagas nada mas.
~~~~

### `eval2 baseline API`

~~~~
Execute this task:
- NO uses ninguna skill, responde de forma normal como lo harias sin instrucciones extra.
- Task: Estamos en fase explore del change 'API de pacientes para app movil y web': alta lectura, pocas escrituras, auth necesaria. Presenta opciones de diseno API.
- Input files: none
- Save outputs to: C:\Users\Cara Palida\Downloads\visual-explore-options-workspace\iteration-1\eval-2-api-arch\without_skill\outputs\
- Crea el directorio si no existe y guarda el resultado como output.md. No hagas nada mas.
~~~~

---

## 4. Los 6 outputs (copiados sin editar)

### `eval-0-frontend-ui` · `with_skill`

1822 bytes · utf-8

`````markdown
## Opcion A: Lista dividida + Calendario lateral
* **Que es?:** Pantalla en dos columnas: lista de pacientes a la izquierda y calendario de huecos a la derecha.
* **Por que y como:** React + Tailwind porque ya es el stack actual, sin librerias nuevas. Se usa con hooks `useState` para paciente seleccionado y `useMemo` para filtrar huecos, componentes `PatientList` y `SlotCalendar` con clases Tailwind para grilla responsive.
* **Trade-off:** Pro: simple de implementar y mantener / Contra: poco denso en movil, requiere scroll entre columnas
* **Esquema:**
```text
+----------------------------------+
| Header: Gestion de Turnos        |
+------------+---------------------+
| Lista      | Calendario huecos   |
| Pacientes  | [9:00][10:00]       |
| - Ana      | [11:00][12:00]       |
+------------+---------------------+
```

## Opcion B: Agenda por franjas horarias
* **Que es?:** Una sola columna tipo agenda donde cada franja horaria muestra su hueco y el paciente asignado o libre.
* **Por que y como:** React + Tailwind porque reutiliza el stack sin dependencias. Se usa con un componente `TimeSlotRow` mapeado desde un array de huecos, `useState` para asignar/liberar turno, y badges de Tailwind para estados libre/ocupado.
* **Trade-off:** Pro: vision clara de huecos libres de un vistazo / Contra: lista de pacientes queda separada en modal o buscador
* **Esquema:**
```text
+----------------------+
| Gestion de Turnos    |
+----------------------+
| 09:00 [ Libre  ]     |
| 10:00 [ Ana    ]     |
| 11:00 [ Libre  ]     |
| 12:00 [ Luis   ]     |
+----------------------+
```

## Recomendacion
Opcion A conviene si priorizas buscar y comparar pacientes; Opcion B conviene si priorizas ver huecos libres rapido.

[PAUSA OBLIGATORIA]
Indica que opcion deseas (A, B, o combinacion) para generar `design.md`.
`````

### `eval-0-frontend-ui` · `without_skill`

1923 bytes · utf-8

`````markdown
# Explore - Pantalla de Gestión de Turnos
Stack: React + Tailwind

Objetivo: mostrar lista de pacientes y huecos disponibles.

## Opción A: Layout Maestro-Detalle (2 columnas)
- Izquierda: lista de pacientes (search + filtro por estado, paginación). Cada row: nombre, DNI, próximo turno, badge estado.
- Derecha: detalle paciente seleccionado + huecos disponibles (calendario semanal + slots por día).
- Pros: rápido para operadoras, selección contextual, poco scroll.
- Contras: en mobile requiere tabs/stack.
- Componentes: `PatientList`, `PatientDetail`, `SlotGrid`, `usePatients`, `useSlots(dateRange)`.

## Opción B: Vista Calendario-first
- Vista principal: calendario semanal con huecos libres/ocupados por profesional/recurso.
- Drawer lateral: buscar y seleccionar paciente, luego click en hueco para asignar.
- Pros: optimiza ocupación, evita solapamientos, ideal si hay muchos profesionales.
- Contras: más complejo (drag & drop, virtualización).
- Componentes: `WeekCalendar`, `PatientSearchDrawer`, `AssignSlotModal`.

## Opción C: Flujo Wizard en 3 pasos
1. Seleccionar paciente (tabla con filtros).
2. Elegir fecha/profesional (filtros + lista de huecos).
3. Confirmar (resumen + validar solape).
- Pros: menos errores, guía a usuarios nuevos, fácil de validar.
- Contras: más clicks para usuarios expertos.
- Componentes: `Stepper`, `StepPatient`, `StepSlot`, `StepConfirm`.

## Recomendación
Empezar con **Opción A** para MVP (más simple, reutiliza tabla + grid), dejando estructura lista para evolucionar a B (calendario) cuando haya multi-profesional. Añadir URL state `?patientId=&date=` para deep-linking y polling/SWR para huecos.

## Datos / API sugerida
- `GET /patients?q=&status=&page=`
- `GET /slots?from=&to=&professionalId=` -> `[{id, start, end, professionalId, status: free|held|booked}]`
- `POST /appointments {patientId, slotId}` con manejo de 409 si el hueco se ocupó.
`````

### `eval-1-backend-db` · `with_skill`

1219 bytes · utf-8

`````markdown
## Opcion A: PostgreSQL + SQLAlchemy
* **Que es?:** Base relacional existente con tablas pacientes y citas ligadas por id.
* **Por que y como:** PostgreSQL porque ya esta en el stack FastAPI. Se usa con SQLAlchemy como ORM para consultas por fecha y paciente + Alembic para migraciones de citas.
* **Trade-off:** Pro: consultas por fecha y paciente con indices rapidas / Contra: requiere modelar schema upfront
* **Esquema:**
```text
[ Cliente ] ---> ( FastAPI / Rutas ) ---> [ PostgreSQL ]
```

## Opcion B: MongoDB Documental
* **Que es?:** Base de documentos donde cada paciente guarda sus citas como lista interna.
* **Por que y como:** MongoDB por esquema flexible para citas de 10k/mes. Se usa con Beanie ODM desde FastAPI para guardar y buscar por fecha y paciente sin migraciones.
* **Trade-off:** Pro: evoluciona rapido sin migraciones / Contra: consultas por fecha cruzada mas lentas
* **Esquema:**
```text
[ Cliente ] ---> ( FastAPI / Rutas ) ---> [ MongoDB ]
```

## Recomendacion
Para 10k citas/mes con consultas por fecha y paciente conviene A por indices y stack existente, B solo si el modelo cambiara mucho.

[PAUSA OBLIGATORIA]
Indica que opcion deseas (A, B, o combinacion) para generar `design.md`.
`````

### `eval-1-backend-db` · `without_skill`

5753 bytes · utf-8

`````markdown
# Explore: Persistencia de Citas y Pacientes
## Contexto: 10k citas/mes, consultas por fecha y paciente | Stack base: FastAPI + PostgreSQL

### Supuestos
- Volumen: 10k citas/mes ≈ 120k/año, ~333/día. Tabla pequeña (<5M filas en 3 años). Cualquier RDBMS lo maneja sin particionado inicial.
- Patrones de acceso dominantes:
  1. `GET /citas?fecha=YYYY-MM-DD` o rango `[desde, hasta]` (agenda diaria/semanal por profesional/sede).
  2. `GET /pacientes/{id}/citas` (historial por paciente, ordenado desc por fecha).
  3. Escrituras: crear/reprogramar/cancelar cita (necesita consistencia: no doble-reserva).
- Requisitos implícitos: ACID para reservas, búsquedas por fecha y FK a paciente, auditoría mínima.

---

### Opción A — PostgreSQL existente (recomendada)
**Descripción:** Seguir con PostgreSQL del stack actual. Modelo relacional normalizado.

**Esquema sugerido:**
```sql
CREATE TABLE pacientes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  documento TEXT UNIQUE NOT NULL,
  telefono TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE citas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paciente_id UUID NOT NULL REFERENCES pacientes(id),
  profesional_id UUID NOT NULL,
  inicio TIMESTAMPTZ NOT NULL,
  fin TIMESTAMPTZ NOT NULL,
  estado TEXT NOT NULL DEFAULT 'programada' CHECK (estado IN ('programada','confirmada','cancelada','completada','ausente')),
  motivo TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  EXCLUDE USING gist (profesional_id WITH =, tstzrange(inicio, fin) WITH && WHERE (estado NOT IN ('cancelada')))
);
CREATE INDEX idx_citas_inicio ON citas (inicio);
CREATE INDEX idx_citas_paciente_inicio ON citas (paciente_id, inicio DESC);
CREATE INDEX idx_citas_profesional_inicio ON citas (profesional_id, inicio);
```

**Pros:**
- Cero costo de adopción, equipo y ORM (SQLAlchemy/SQLModel) ya listos.
- ACID + `EXCLUDE` constraint evita solapamientos sin lógica aplicativa propensa a race conditions.
- Índices B-tree cubren los 2 queries principales; `EXPLAIN` predecible.
- Migraciones con Alembic, backup/PITR maduros.

**Contras:**
- Si a futuro se agregan recordatorios / búsqueda full-text de notas clínicas, requiere extensiones (`pg_trgm`, `pg_cron`).

**Costo/Operación:** Bajo. Una instancia pequeña (1-2 vCPU, 4GB RAM) sobra para este volumen.

**Cuándo elegirla:** Por defecto. Es la opción de menor riesgo para 10k/mes.

---

### Opción B — PostgreSQL + particionado por rango mensual
**Descripción:** Misma que A pero `citas` particionada por `RANGE (date_trunc('month', inicio))`.

**Pros:**
- Purgado/archivado barato (`DETACH PARTITION`), VACUUM más rápido.
- Útil si retención >5 años o se requieren reportes pesados sin afectar agenda caliente.

**Contras:**
- Complejidad innecesaria hoy: con 120k filas/año el planner no gana nada; particionar prematuro complica FKs y el constraint `EXCLUDE` (no funciona cross-partition en PG nativo, habría que enforcement en app o trigger).
- Mayor fricción en Alembic/tests.

**Veredicto:** Descartar por ahora; reconsiderar a >1M citas/año o >10M filas.

---

### Opción C — MongoDB / Document store (alternativa NoSQL)
**Descripción:** Colecciones `pacientes` y `citas` con documentos embebidos, índices en `inicio` y `paciente_id`.

**Pros:**
- Esquema flexible si la ficha de cita cambia mucho (formularios dinámicos, adjuntos).
- Escrituras rápidas, sharding horizontal sencillo.

**Contras:**
- Sin `EXCLUDE` equivalente: evitar doble-reserva exige transacción + índice único parcial artesanal o lock aplicativo → más bugs de concurrencia.
- Joins (`$lookup`) y reportes por fecha+profesional menos eficientes que SQL.
- Introduce nueva tecnología, backup/monitoreo y curva de aprendizaje sin justificación de volumen (10k/mes no necesita escala horizontal).

**Veredicto:** Solo si el producto pivota a datos clínicos no estructurados masivos. No recomendada para agenda transaccional.

---

### Opción D — SQLite + Litestream / Supabase Postgres gestionado (alternativa low-ops)
**Descripción:** Delegar ops: Supabase/Neon/RDS para PG, o SQLite para dev/local-first.

**Pros:**
- Managed PG elimina backup, HA, PITR.
- SQLite: cero ops para MVP single-node.

**Contras:**
- SQLite no sirve para FastAPI multi-worker con escrituras concurrentes (locks) ni 10k/mes multi-sede.
- Managed PG tiene costo recurrente y posible latencia si la app es on-prem.

**Veredicto:** Usar PG gestionado (Supabase/Neon) como *despliegue* de la Opción A, no como cambio de modelo. SQLite solo para tests/dev.

---

### Comparativa rápida

| Criterio | A: PG simple | B: PG particionado | C: Mongo | D: Managed/SQLite |
|---|---|---|---|---|
| Consistencia anti-solape | Excelente (EXCLUDE) | Mala (no cross-partition) | Débil (app-level) | Igual que A / Débil en SQLite |
| Query por fecha | Excelente | Excelente | Buena | Excelente / Buena |
| Query por paciente | Excelente | Excelente | Buena | Excelente |
| Complejidad | Baja | Media-Alta | Media (nuevo stack) | Baja |
| Costo 10k/mes | Bajo | Bajo+ | Medio (nuevo cluster) | Bajo-Medio |
| Escalabilidad futura | Vertical hasta ~50M filas | Mejor para archivado | Mejor sharding | Igual que A |

---

### Recomendación
**Adoptar Opción A (PostgreSQL existente, modelo normalizado + 3 índices + EXCLUDE constraint).** Desplegar sobre PG gestionado si se quiere reducir ops (variante de D). No particionar ni migrar a NoSQL con el volumen actual.

**Siguientes pasos:**
1. Definir estados de cita y transiciones permitidas.
2. Confirmar granularidad de agenda (slots de 15/30 min, multi-profesional).
3. Migración Alembic inicial + seed + test de concurrencia (2 reservas solapadas simultáneas deben fallar una).
`````

### `eval-2-api-arch` · `with_skill`

1500 bytes · utf-8

`````markdown
## Opcion A: REST con cache + JWT
* **Que es?:** API por rutas ordenadas (/pacientes, /pacientes/:id) que guarda en base relacional y guarda lecturas repetidas en cache.
* **Por que y como:** JWT para auth necesaria en movil y web con el mismo token. Lecturas altas se sirven desde Redis para no golpear la DB. Escrituras pocas van directo a PostgreSQL con ORM + migraciones.
* **Trade-off:** Pro: simple y rapido para lecturas / Contra: el cache hay que invalidarlo al escribir
* **Esquema:**
```text
[ Movil / Web ] ---> ( API REST / Auth JWT ) ---> [ Cache Redis ]
                                    |
                                    v
                              [ PostgreSQL ]
```

## Opcion B: GraphQL con auth central
* **Que es?:** Un solo punto (/graphql) donde movil y web piden solo los campos de paciente que necesitan.
* **Por que y como:** GraphQL evita traer fichas completas cuando la app solo necesita nombre y turno. Auth con JWT en cada query + DataLoader para agrupar lecturas a PostgreSQL y no saturar la DB.
* **Trade-off:** Pro: menos datos por red, ideal movil / Contra: mas complejo de cachear y proteger
* **Esquema:**
```text
[ Movil / Web ] ---> ( GraphQL / Auth JWT ) ---> [ PostgreSQL ]
```

## Recomendacion
Para alta lectura y pocas escrituras, la Opcion A conviene por cache simple y menor costo. Si movil necesita ahorrar datos, combina con campos selectivos de B.

[PAUSA OBLIGATORIA]
Indica que opcion deseas (A, B, o combinacion) para generar `design.md`.
`````

### `eval-2-api-arch` · `without_skill`

2776 bytes · utf-8

`````markdown
# Explore: API de Pacientes para App Móvil y Web

Contexto: alta lectura, pocas escrituras, auth necesaria.

## Opción 1: REST + JWT (stateless) + Cache
- Diseño: recursos `/patients`, `/patients/{id}`, `/patients/{id}/history`. Autenticación con JWT (access corto + refresh). Paginación cursor-based para listas. ETag / `Cache-Control` + Redis para lecturas frecuentes.
- Pros: simple, estándar, fácil de consumir desde móvil y web. Escalado horizontal trivial por stateless. Cache reduce carga en lecturas.
- Contras: over-fetching en móvil si el modelo paciente es grande. Versionado necesario (`/v1`).
- Ideal cuando: equipo pequeño, time-to-market prioritario.

## Opción 2: GraphQL (lecturas flexibles) + Auth por contexto
- Diseño: un endpoint `/graphql` con queries `patient(id)`, `patientsConnection(first, after, filter)`. Auth via JWT en header, directivas `@auth` por rol (médico, paciente, admin). DataLoader para evitar N+1.
- Pros: óptimo para móvil (pide solo campos necesarios). Evoluciona sin versionado. Bueno para alta lectura con formas de consumo distintas web vs móvil.
- Contras: cacheo HTTP más complejo (requiere persisted queries + CDN). Mayor superficie de complejidad: rate-limit por costo de query, análisis de queries.
- Ideal cuando: clientes con necesidades de datos divergentes.

## Opción 3: REST Lectura + CQRS ligero (Read replicas / materialized views)
- Diseño: separación lectura/escritura. Escrituras: `POST /patients`, `PATCH /patients/{id}` con validación estricta + audit log. Lecturas: endpoints optimizados de solo-lectura (`GET /patients/summary`, `/patients/search?q=`) servidos desde réplica read-only o vista materializada + Redis.
- Pros: mejor rendimiento en alta lectura sin penalizar consistencia de escritura. Seguridad clara: scopes distintos `patients:read` vs `patients:write`.
- Contras: eventual consistency en lecturas si se usa réplica. Más infraestructura.
- Ideal cuando: volumen de lectura >10x escritura y se requiere búsqueda/filtrado rápido.

## Comparativa rápida

| Criterio | REST+JWT | GraphQL | REST CQRS ligero |
|---|---|---|---|
| Simplicidad | Alta | Media | Media |
| Performance lectura | Alta (con cache) | Alta (menos bytes) | Muy alta |
| Flexibilidad cliente | Baja | Alta | Media |
| Auth / scopes | Simple (JWT scopes) | Por campo/tipo | Separada read/write |
| Cache | Fácil | Difícil | Fácil |

## Recomendación
Empezar con **Opción 1 (REST + JWT + Redis cache)** con paginación por cursor y scopes OAuth2 (`patients:read`, `patients:write`). Si móvil y web divergen mucho en datos, migrar lecturas a GraphQL manteniendo escrituras REST (híbrido). Añadir rate-limit por usuario, audit de escrituras, y cifrado PII en reposo por ser datos de pacientes.
`````

---

## 5. Los criterios evaluados

Cada eval declaró las mismas 5 `assertions`. Copia literal de los tres `eval_metadata.json`:

~~~~json
{"eval_id": 0, "eval_name": "eval-0-frontend-ui", "prompt": "pantalla de gestion de turnos React+Tailwind", "assertions": ["Presenta al menos 2 opciones", "Cada opcion tiene Que es + Por que/como + Trade-off", "Incluye esquema ASCII en bloque text", "Termina con pausa obligatoria sin generar design.md", "Incluye recomendacion explicita"]}
~~~~

~~~~json
{"eval_id": 1, "eval_name": "eval-1-backend-db", "prompt": "persistencia de citas y pacientes FastAPI+PG", "assertions": ["Presenta al menos 2 opciones", "Cada opcion tiene Que es + Por que/como + Trade-off", "Incluye esquema ASCII en bloque text", "Termina con pausa obligatoria sin generar design.md", "Incluye recomendacion explicita"]}
~~~~

~~~~json
{"eval_id": 2, "eval_name": "eval-2-api-arch", "prompt": "API de pacientes movil y web", "assertions": ["Presenta al menos 2 opciones", "Cada opcion tiene Que es + Por que/como + Trade-off", "Incluye esquema ASCII en bloque text", "Termina con pausa obligatoria sin generar design.md", "Incluye recomendacion explicita"]}
~~~~

---

## 6. Corrección de cada criterio en cada corrida

Copia literal de los `expectations` de `benchmark.json` (2 configuraciones × 3 evals × 5 criterios = 30):

| Corrida | Eval | Criterio | Pasa | Evidencia |
|---|---|---|---|---|
| `with_skill` | eval-0-frontend-ui | Presenta al menos 2 opciones | sí | 2 opciones con formato completo y ASCII |
| `with_skill` | eval-0-frontend-ui | Cada opcion tiene Que es + Por que/como + Trade-off | sí | output.md lineas 2-4, 17-19 |
| `with_skill` | eval-0-frontend-ui | Incluye esquema ASCII en bloque text | sí | bloques ```text lineas 6-14, 21-30 |
| `with_skill` | eval-0-frontend-ui | Termina con pausa obligatoria sin generar design.md | sí | lineas 35-36 pausa, no genera design.md |
| `with_skill` | eval-0-frontend-ui | Incluye recomendacion explicita | sí | lineas 32-33 |
| `without_skill` | eval-0-frontend-ui | Presenta al menos 2 opciones | sí | 3 opciones |
| `without_skill` | eval-0-frontend-ui | Cada opcion tiene Que es + Por que/como + Trade-off | no | usa formato propio Pros/Contras, no Que es/Por que |
| `without_skill` | eval-0-frontend-ui | Incluye esquema ASCII en bloque text | no | sin bloque ASCII |
| `without_skill` | eval-0-frontend-ui | Termina con pausa obligatoria sin generar design.md | no | termina con API sugerida, sigue de largo |
| `without_skill` | eval-0-frontend-ui | Incluye recomendacion explicita | sí | tiene recomendacion MVP |
| `with_skill` | eval-1-backend-db | Presenta al menos 2 opciones | sí | 2 opciones PG vs Mongo |
| `with_skill` | eval-1-backend-db | Cada opcion tiene Que es + Por que/como + Trade-off | sí | formato completo |
| `with_skill` | eval-1-backend-db | Incluye esquema ASCII en bloque text | sí | bloques text flujo |
| `with_skill` | eval-1-backend-db | Termina con pausa obligatoria sin generar design.md | sí | pausa final |
| `with_skill` | eval-1-backend-db | Incluye recomendacion explicita | sí | recomendacion A |
| `without_skill` | eval-1-backend-db | Presenta al menos 2 opciones | sí | 4 opciones A-D |
| `without_skill` | eval-1-backend-db | Cada opcion tiene Que es + Por que/como + Trade-off | no | formato libre detallado, no plantilla |
| `without_skill` | eval-1-backend-db | Incluye esquema ASCII en bloque text | no | SQL pero no ASCII flujo |
| `without_skill` | eval-1-backend-db | Termina con pausa obligatoria sin generar design.md | no | termina con siguientes pasos, no pausa |
| `without_skill` | eval-1-backend-db | Incluye recomendacion explicita | sí | recomendacion A detallada |
| `with_skill` | eval-2-api-arch | Presenta al menos 2 opciones | sí | REST vs GraphQL |
| `with_skill` | eval-2-api-arch | Cada opcion tiene Que es + Por que/como + Trade-off | sí | formato completo |
| `with_skill` | eval-2-api-arch | Incluye esquema ASCII en bloque text | sí | bloques text |
| `with_skill` | eval-2-api-arch | Termina con pausa obligatoria sin generar design.md | sí | pausa final |
| `with_skill` | eval-2-api-arch | Incluye recomendacion explicita | sí | recomendacion A |
| `without_skill` | eval-2-api-arch | Presenta al menos 2 opciones | sí | 3 opciones |
| `without_skill` | eval-2-api-arch | Cada opcion tiene Que es + Por que/como + Trade-off | no | formato propio |
| `without_skill` | eval-2-api-arch | Incluye esquema ASCII en bloque text | no | sin ASCII |
| `without_skill` | eval-2-api-arch | Termina con pausa obligatoria sin generar design.md | no | sin pausa |
| `without_skill` | eval-2-api-arch | Incluye recomendacion explicita | sí | recomendacion REST+JWT |

### Totales (`result` de cada corrida)

| Corrida | Eval | Pasan | Fallan | Tasa |
|---|---|---|---|---|
| `with_skill` | eval-0-frontend-ui | 5 | 0 | 1.00 |
| `without_skill` | eval-0-frontend-ui | 2 | 3 | 0.40 |
| `with_skill` | eval-1-backend-db | 5 | 0 | 1.00 |
| `without_skill` | eval-1-backend-db | 2 | 3 | 0.40 |
| `with_skill` | eval-2-api-arch | 5 | 0 | 1.00 |
| `without_skill` | eval-2-api-arch | 2 | 3 | 0.40 |

### Resumen agregado (`run_summary`) y notas

~~~~json
{
  "run_summary": {
    "delta": {
      "pass_rate": "+0.60",
      "time_seconds": "+0.0",
      "tokens": "+0"
    },
    "with_skill": {
      "pass_rate": {
        "max": 1.0,
        "mean": 1.0,
        "min": 1.0,
        "stddev": 0.0
      },
      "time_seconds": {
        "max": 0,
        "mean": 0,
        "min": 0,
        "stddev": 0
      },
      "tokens": {
        "max": 0,
        "mean": 0,
        "min": 0,
        "stddev": 0
      }
    },
    "without_skill": {
      "pass_rate": {
        "max": 0.4,
        "mean": 0.4,
        "min": 0.4,
        "stddev": 0.0
      },
      "time_seconds": {
        "max": 0,
        "mean": 0,
        "min": 0,
        "stddev": 0
      },
      "tokens": {
        "max": 0,
        "mean": 0,
        "min": 0,
        "stddev": 0
      }
    }
  },
  "notes": [
    "with_skill estandariza plantilla y pausa 100% vs 40% baseline",
    "baseline da mas profundidad tecnica (SQL DDL, EXCLUDE, 3-4 opciones) pero sin pausa ni formato",
    "trade-off: simplicidad vs profundidad - considerar permitir detalle opcional"
  ],
  "metadata": {
    "analyzer_model": "manual",
    "evals_run": [
      0,
      1,
      2
    ],
    "executor_model": "muse-spark",
    "runs_per_configuration": 1,
    "skill_name": "visual-explore-options",
    "skill_path": "C:\\Users\\Cara Palida\\Downloads\\visual-explore-options",
    "timestamp": "2026-10-16T00:00:00Z"
  }
}
~~~~

---

## 7. Límites de esta evidencia

1. **`time_seconds`, `tokens` y `tool_calls` están en `0`** en `benchmark.json`. No se midieron; no los interpreto como medición.
2. **`analyzer_model` es `manual`** en el metadata del benchmark: la corrección de los criterios la hizo el agente
   revisando los archivos, no un grader automático. Así consta en el archivo.
3. **No existe `grading.json` ni `feedback.json`** en el workspace. El `review.html` sí está (69758 bytes) y se abrió
   en la sesión con `browser.preview`, pero el `feedback.json` de esa revisión nunca se escribió y la iteración 2
   propuesta no se ejecutó.
4. Las 6 salidas se copiaron tal cual; los caracteres que no son ASCII (`é`, `ñ`, etc.) se conservan tal como
   están en los archivos de origen.
