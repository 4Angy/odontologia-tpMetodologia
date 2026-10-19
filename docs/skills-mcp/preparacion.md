# Informe de Preparación - TP Skills y MCP (Punto 7)
## Exploración del change pendiente y generación de sus artefactos SDD
### Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)
### Fecha
2026-10-19
### Change
C-02 tenancy-core-models — **preparado para implementar** (0/46 tareas; no implementado, no verificado, no archivado)
### Consigna del punto 7
"Realicen la exploración del change pendiente y generen o revisen sus artefactos: especificaciones y proposal.md, design.md, tasks.md, respetando el flujo SDD del proyecto. Utilicen la skill propia y una herramienta del MCP en tareas concretas de esa preparación. Si cambian la elección respecto de la ficha inicial, expliquen el motivo. La especificación debe contener al menos tres escenarios verificables: uno de funcionamiento esperado, uno de error de negocio y uno de borde. Las tareas deben incluir cómo se verificará cada escenario cuando se implemente. Revisen las reglas contra la base de conocimiento y no incorporen decisiones de dominio sin justificarlas. Dejen el change preparado para implementar y actualicen su referencia en el roadmap según las convenciones existentes. No lo marquen como implementado, verificado o archivado."
### 1. Elección del change y motivo del cambio respecto de la ficha inicial
La ficha de investigación (`investigacion.md` §2) declara como change candidato para el punto 7 a `C-01 foundation-setup-decisiones`, primer change del camino crítico y sin dependencias.
**Motivo del cambio de elección**: C-01 fue implementado, verificado y **archivado** durante esta sesión (`openspec/changes/archive/2026-10-19-C-01-foundation-setup-decisiones/`). La consigna exige dejar un change **preparado para implementar** y **no** marcarlo implementado ni archivado, lo que es incompatible con reutilizar C-01 sin deshacer su cierre.
**Change elegido**: `C-02 tenancy-core-models` — GATE 1 del roadmap, desbloqueado (depende de C-01, ya archivado), en el camino crítico y **desbloquea todo lo demás** (C-03 abre el abanico). Tiene decisiones técnicas reales y está gobernado por reglas concretas de la base de conocimiento.
Alternativas descartadas: C-03 (mezcla backend y frontend, y es CRITICO: el change preparado sería mayor que el de la consigna); C-07 (depende de C-04 y C-06, que no están desbloqueados, así que no podría quedar "preparado para implementar").
El cambio de elección queda documentado en `discovery/explore-c02-tenancy-core-models.md` §0.
### 2. Exploración con la skill propia
**Skill utilizada**: `visual-explore-options` (propia del proyecto), invocada con `skill({ id: "visual-explore-options" })`.
**Procedimiento aplicado**: contexto del change y de la KB -> restricciones duras -> al menos 2 alternativas por decisión -> esquema ASCII -> plantilla exacta -> recomendación -> **pausa obligatoria**.
**Artefacto**: `discovery/explore-c02-tenancy-core-models.md` (4 ejes x 2 opciones, alternativas descartadas con su razonamiento, esquemas ASCII y §8 de deudas diferidas con owner).
**Las 4 decisiones comparadas**:
- Eje 1 — Migración 002: A) altera y completa las tablas que `0001` ya creó; B) reconstruye `tenant` y `config` desde la KB. Elegida **A** (no se tira código validado; `0001` no se toca).
- Eje 2 — `roles`: A) `ARRAY` de enum de Postgres; B) tabla puente `usuario_rol` + catálogo. Elegida **A** (es lo que dice KB §04; B contradice la KB y suma dos tablas a un change CRITICO).
- Eje 3 — Aislamiento R1: A) repositorio *tenant-scoped*, el filtro lo aplica el `UnitOfWork`; B) `tenant_id` explícito en cada llamada. Elegida **A** (R1 deja de depender de la disciplina).
- Eje 4 — Seed: A) comando explícito `python -m app.seed`; B) seed automático al arrancar. Elegida **A** (un `SEED_DEMO=true` en un entorno real no siembra datos demo en producción).
**La pausa obligatoria se respetó**: no se generó `proposal.md` ni `design.md` hasta que el usuario respondió "aplica las opciones que recomendaste".
### 3. Herramienta del MCP utilizada en la preparación
**Servidor**: `filesystem` (`@modelcontextprotocol/server-filesystem`, oficial de Anthropic) — el seleccionado en `investigacion.md` §4.
**Cliente**: `docs/skills-mcp/tools/mcp-fs.js`, que habla JSON-RPC 2.0 por stdio (`initialize` -> `tools/list` -> `tools/call`) con la raíz del proyecto. Hace falta porque la instancia que abre el cliente de OpenCode queda rooteada en el workspace de la sesión, y porque el shim `npx.cmd` de Windows parte el path del workspace al contener un espacio.
**Solicitudes realizadas y resultados obtenidos**:
- `list_directory` sobre `knowledge-base/` -> los 10 archivos de la KB más el README.
- `read_text_file` sobre `knowledge-base/04_modelo_de_datos.md` -> 6.041 caracteres: atributos de `tenant` (id uuid PK, slug unique global, nombre, email_contacto, tz, created_at), de `usuario` (email unique por tenant, `roles` **array enum** `recepcion/odontologo/dueno`, activo, password_hash), de `config` (antelacion_hs, senia_monto, plantillas), la regla *"Toda tabla de negocio lleva `tenant_id` NOT NULL + FK a `tenant`. Unicidades y búsquedas siempre compuestas con `tenant_id`"* y la sección de seed.
- `read_text_file` sobre `knowledge-base/03_actores_y_roles.md` -> 3.022 caracteres: *"Roles: `recepcion` · `odontologo` · `dueno`. `dueno` incluye todo. Un usuario puede acumular roles."*
**Qué aportó al change**: los atributos de los tres modelos, la unicidad compuesta, el seed y el nombre real de los roles. Sin esa lectura, la decisión del eje 2 habría sido una preferencia técnica; con ella, es una cita de la KB §04, y la alternativa de la tabla puente queda descartada **por contradecir la KB**. También permitió detectar una inconsistencia interna de la KB (el ERD lista `config(antelacion_hs, senia_monto, plantillas)` y el seed dice `antelacion_cancel_hs = 24`, `senia_requerida = false`), que quedó registrada como desviación con owner en vez de resolverse por decreto.
### 4. Artefactos generados
Están en `openspec/changes/C-02-tenancy-core-models/`.
- **proposal.md** — por qué, qué cambia, capabilities (`tenancy/identidad` como nueva; ninguna modificada) e impacto.
- **design.md** — contexto verificado, goals/non-goals, **13 decisiones** con rationale y alternativa descartada cada una, riesgos con mitigación, plan de migración y preguntas abiertas.
- **specs/tenancy/identidad/spec.md** — 5 requirements y 13 escenarios (ver §5).
- **tasks.md** — 46 tareas en 8 grupos, cada una con su verificación (ver §6).
- **discovery/explore-c02-tenancy-core-models.md** — el artefacto de la skill, fuera del change porque es el insumo de la exploración.
### 5. La especificación: 13 escenarios verificables
Capability `tenancy/identidad` (dominio "Tenancy/identidad" de KB §04). 5 requirements:
1. Aislamiento por tenant en la capa de datos.
2. Rechazo de operaciones sin tenant autenticado.
3. Identidad global del tenant por `slug`.
4. Roles acumulables con permiso por unión.
5. Auditoría mínima de toda mutación.
6. Seed de demostración idempotente.
Distribución por tipo, con el tipo etiquetado en el nombre de cada escenario: **4 de funcionamiento esperado**, **2 de error de negocio**, **7 de borde**. La consigna pedía al menos uno de cada tipo.
### 6. Las tareas y cómo se verifica cada escenario
Los **13 escenarios están referenciados uno a uno** en `tasks.md`, con la tarea que lo cubre y su comando de verificación. Ejemplos:
- Escenario 1.1 (funcionamiento esperado) -> tarea 2.5: el acceso a datos del tenant A no devuelve el usuario del tenant B, y el filtro no puede omitirse.
- Escenario 2.1 (error de negocio) -> tarea 3.1: token sin `tenant_id` responde `403` con `code: RN-AU-01` y no ejecuta ninguna consulta de datos.
- Escenario 3.1 (error de negocio) -> tarea 4.1: segundo tenant con el mismo `slug` es rechazado por la restricción de unicidad.
- Escenario 4.1 (funcionamiento esperado) -> tarea 5.1: un usuario con `recepcion` + `odontologo` puede leer la agenda y registrar su atención, sin un segundo usuario.
- Escenario 6.1 (funcionamiento esperado) -> tarea 7.1: el seed ejecutado dos veces deja el mismo número de tenants y usuarios.
Verificación de la suite: `pytest` contra **Postgres 16 real** (cada test en su propio esquema), `alembic upgrade head` -> `downgrade -1` -> `upgrade head` para la reversibilidad (R6), `openspec validate --strict`, y el ciclo de seed en el compose.
### 7. Reglas revisadas contra la base de conocimiento
Se revisaron las 10 secciones de la KB contra el contenido del change. Cada decisión de dominio quedó atada a una sección: §03 (roles), §04 (modelo y seed), §05 (RN-AU-01, RN-AU-04, RN-GL-02, RN-CO-02), §08 (patrones), §09 (DD-04, DD-06).
**No se incorporaron decisiones de dominio sin justificar**: donde la KB no llegaba, el change no inventó. `config` crece sólo con `senia_requerida` (RN-CO-02 y seed §04); `plantillas` y las ventanas de recordatorio quedan para C-06 y C-09, que son sus dueños; el catálogo de roles queda fuera porque §04 define los roles embebidos en v1; RLS queda diferida a C-13 porque DD-04 la marca como endurecimiento posterior.
**Desviaciones registradas con owner** (task 1.9): `tenant.id` queda como `String(64)` en vez de uuid de §04, porque `turno.tenant_id` (FK creado en `0001`) es `String(64)` y cambiar la PK obligaría a re-migrar el slice archivado; y la columna real se llama `antelacion_cancel_hs`, no `antelacion_hs` del ERD.
### 8. Estado del change y del roadmap
- `openspec list` -> `C-02-tenancy-core-models  0/46 tasks`: change **activo**.
- `openspec validate C-02-tenancy-core-models --strict` -> valid. `openspec validate --all --strict` -> 3/3.
- `CHANGES.md` conserva la convención del repo (`[ ]` pendiente de implementación) y agrega la referencia: *"artefactos SDD listos en `openspec/changes/C-02-tenancy-core-models/`... **No implementado, no verificado, no archivado.**"*, más las decisiones tomadas y las desviaciones a registrar.
- **No se implementó nada**: 0 tareas hechas, ningún archivo de `backend/` o `frontend/` tocado, el spec no se archivó.
### Archivos modificados y motivo
| Archivo | Motivo |
|---------|--------|
| `openspec/changes/C-02-tenancy-core-models/proposal.md` | Punto 7: propuesta del change (por qué, qué, capabilities, impacto) |
| `openspec/changes/C-02-tenancy-core-models/design.md` | Punto 7: diseño técnico con 13 decisiones, riesgos, plan de migración |
| `openspec/changes/C-02-tenancy-core-models/specs/tenancy/identidad/spec.md` | Punto 7: contrato de comportamiento con 13 escenarios verificables |
| `openspec/changes/C-02-tenancy-core-models/tasks.md` | Punto 7: 46 tareas con la verificación de cada escenario |
| `openspec/changes/C-02-tenancy-core-models/.openspec.yaml` | Punto 7: metadatos del change para OpenSpec |
| `discovery/explore-c02-tenancy-core-models.md` | Punto 7: artefacto del explore generado con la skill |
| `CHANGES.md` | Punto 7: referencia del change en el roadmap, conservando la convención y sin marcarlo implementado |
| `docs/skills-mcp/preparacion.md` | Punto 7: este informe |
| `docs/skills-mcp/TP-preparacion-puntos-7.pdf` | Punto 7: versión PDF de este informe |
| `docs/skills-mcp/tools/mcp-fs.js` | Punto 7: cliente MCP stdio reutilizable con la raíz del proyecto |
### Limitaciones
- Los dos MCP del proyecto siguen con raíces distintas: `engram` resuelve el proyecto por el directorio de la sesión (`Downloads`), no por el repositorio; `filesystem` se consultó con el cliente stdio apuntando a la raíz del repo.
- El `explore` se apoya en la KB leída por MCP, no en el código de C-03 a C-13, que todavía no existe: por eso el design deja explícitos los non-goals (auth, RLS, catálogo de roles, plantillas).
- La desviación de `tenant.id` se acepta con owner C-06/C-07 y criterio de re-evaluación; si el volumen de tenants justificara el cambio a uuid, debe migrar también `turno.tenant_id` en el mismo paso.
- La consigna pide "al menos tres escenarios" y el spec tiene trece: el excedente viene de que cada requirement necesita al menos un caso de funcionamiento y la KB exige cubrir también el error de negocio y el borde.
