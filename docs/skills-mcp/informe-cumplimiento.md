# Informe de Cumplimiento — TP Skills y MCP

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)
**Change principal:** `C-02 tenancy-core-models` — *preparado para implementar*
**Fecha:** 2026-10-19 · **Para:** exposición oral del trabajo

---

## 1. Resumen ejecutivo

El TP pedía tres cosas: **una skill propia**, **un servidor MCP** y **la preparación de un change pendiente** usando ambos. Se entregaron las tres, más la implementación y el archivado del change anterior (`C-01`), que era el que estaba pendiente al empezar.

| Entrega | Estado | Dónde |
|---|---|---|
| Skill propia `visual-explore-options` | ✅ integrada en 4 rutas del repo + global, registrada y referenciada | `.opencode/skills/`, `.atl/skill-registry.md`, `AGENTS.md` |
| MCP `filesystem` (oficial Anthropic) | ✅ **conectado y operativo**, con herramienta real ejecutada | `~/.config/opencode/opencode.json`, `docs/skills-mcp/tools/mcp-fs.js` |
| Change `C-02` preparado | ✅ 4/4 artefactos, **0/46 tareas** (no implementado, no verificado, no archivado) | `openspec/changes/C-02-tenancy-core-models/` |
| Revisión crítica | ✅ 8 defectos con antes/después + prueba de borde | `docs/skills-mcp/revision-critica.md` |
| `.zip` de entrega + `ENTREGA.md` | ✅ `TP-Skills-MCP-Herrera-Zalazar.zip` generado por script (32 entradas) | `ENTREGA.md`, `docs/skills-mcp/tools/entrega.ps1` |
| Video de 5 minutos | ➖ **no se graba** (decisión del equipo); la evidencia en texto de las invocaciones cubre lo mismo | `docs/skills-mcp/evidencias/` |

---

## 2. Mapa de cumplimiento, consigna por consigna

| # | Consigna | Cómo se cumplió | Evidencia |
|---|---|---|---|
| 1 | Necesidad real; change de `CHANGES.md` preparable; tarea repetible para la skill; necesidad de acceso para el MCP; **cómo ambos ayudan al mismo change** | Skill para estandarizar el `explore` (comparar opciones y **detenerse**); MCP para leer la KB y el repo sin salir del chat. Ambos se usaron en la preparación de C-02 | `investigacion.md` §1-§2 |
| 2 | Skill creadora (nombre, fuente, compatibilidad); cómo instalarla y usarla; **6 elementos** de diseño de la skill; dónde guardarla | `skill-creator` (OpenCode) — fuente oficial, compatibilidad verificada. Diseño con propósito, activación, entradas, procedimiento, resultado esperado y criterios de revisión | `investigacion.md` §3, §7 |
| 3 | **Comparar 2 MCP** en 7 dimensiones; elegir uno; documentar configuración y **cómo comprobar la conexión y ejecutar una herramienta**; qué se consulta y qué límites | Filesystem vs GitHub en propósito, capacidades, compatibilidad, instalación, permisos, credenciales y costos. Elección justificada. Conexión y herramienta real documentadas | `investigacion.md` §4-§5, `mcp-configuracion.md` |
| 4 | Ficha de **hasta 2 páginas** con 7 elementos y fuentes con URL y fecha | `investigacion.md` — 2 páginas en PDF, los 7 elementos, 6 fuentes con URL y fecha | `TP-investigacion-puntos-1-a-4.pdf` |
| 5 | Crear e integrar la skill; copia versionada si es global; **registro**; `AGENTS.md`; coherencia; documentar qué se modificó; comprobación en sesión nueva | Instalada en `.opencode/`, `.claude/`, `.devin/` y `skills/` (+ global). Registrada en `.atl/skill-registry.md` con los 4 campos pedidos. `AGENTS.md` actualizado. 6 pruebas con/sin skill: **15/15 vs 6/15** | `AGENTS.md`, `.atl/skill-registry.md`, `aplicacion.md` §1 |
| 6 | Configurar el MCP; **comprobar conexión y ejecutar ≥1 herramienta real**; documentar requisitos, pasos, variables, comprobación y **solución de un problema de instalación**; configuración de ejemplo sin secretos; actualizar instrucciones del agente sin registrarlo como skill | Conectado y verificado con handshake JSON-RPC. Problema de instalación **resuelto y documentado**. Config sin secretos. En `AGENTS.md` §Integración MCP, explícitamente como integración | `mcp-configuracion.md`, `evidencias/mcp-filesystem-verificacion.txt` |
| 7 | Explorar el change y generar/revisar proposal, design, specs y tasks; **usar la skill y una herramienta del MCP**; explicar el cambio de elección; ≥3 escenarios (funcionamiento, error de negocio, borde); tareas con **cómo se verifica**; contrastar con la KB; dejar el change **preparado** y actualizar el roadmap **sin marcarlo implementado** | Explore con la skill (4 ejes, A/A/A/A) + MCP para leer §03/§04 de la KB. Spec con **13 escenarios** (4 funcionamiento, 2 error de negocio, 7 borde) y **46 tareas** con la verificación de cada uno. Sin decisiones de dominio sin justificar. `CHANGES.md` con la convención `[ ]` y la nota *"No implementado, no verificado, no archivado"* | `preparacion.md`, `openspec/changes/C-02-tenancy-core-models/` |
| 8 | Evidencia de **invocación** de skill y MCP (solicitud, resultado, aportación); **≥1 omisión, error o sugerencia inadecuada** con detección, fuente/regla y antes/después; o prueba de borde de los límites | Evidencia de las dos invocaciones y **8 defectos** con antes/después, más una prueba de borde que **muestra que `openspec validate` no detecta** las contradicciones entre specs | `revision-critica.md`, `evidencias/defectos-antes-despues.md` |
| Entrega | Repositorio actualizado con historial de commits; ficha e informe de ≤2 págs; **un `.zip` único** con `ENTREGA.md`; repo con artefactos e instrucciones de reproducción | 11 commits que muestran el proceso. Ficha e informe en 2 págs. `ENTREGA.md` + script de empaquetado. **Pendiente:** ejecutar el `.zip` con los apellidos y subir el video | `ENTREGA.md` |
| Consideraciones | Datos ficticios; **sin credenciales** ni secretos; alcance con ambas incorporaciones; reproducibilidad; registrar los problemas de acceso o compatibilidad | R14 y `SEED_DEMO` con datos sintéticos; cero secretos (verificado por test automático sobre los `.env.example`); skill y MCP integrados y documentados; pasos de reproducción en `ENTREGA.md` §4; **3 problemas de compatibilidad resueltos y documentados** (ver §6) | `evidencias/`, `ENTREGA.md` |

---

## 3. Las dos incorporaciones

### 3.1 La skill `visual-explore-options`

**Qué es:** instrucciones reutilizables para que el agente estandarice la fase `explore` del flujo SDD: presenta **al menos 2 alternativas técnicas comparables** (qué es / por qué y cómo / trade-off / esquema ASCII), recomienda una y **se detiene** hasta que la persona elija.

**Por qué era necesaria:** sin ella, cada agente comparaba opciones con un formato distinto y, sobre todo, **no esperaba la decisión del usuario** — el riesgo mayor de esa fase es decidir por el usuario. La skill convierte ese comportamiento en un paso explícito y con criterio de revisión.

**Dónde está:** `.opencode/skills/visual-explore-options/SKILL.md` (repo, fuente de verdad) + réplicas en `.claude/skills/`, `.devin/skills/` y `skills/visual-explore-options.md` + instalación global en `~/.config/opencode/skills/`. Registrada en `.atl/skill-registry.md` y en `AGENTS.md` §Skills disponibles.

**Evidencia de uso:** el explore de C-02 (`discovery/explore-c02-tenancy-core-models.md`) con 4 ejes comparados y la pausa obligatoria respetada; más 6 pruebas de `skill-creator` (**con skill 15/15 vs. baseline 6/15**).

### 3.2 El MCP `filesystem`

**Qué es:** el servidor oficial de Anthropic que expone 14 herramientas sobre el sistema de archivos local, con la raíz acotada al repositorio.

**Por qué era necesario:** el agente tenía que consultar `knowledge-base/`, `CHANGES.md` y `openspec/` repetidamente, y con herramientas nativas del cliente salía del chat con permisos amplios; el MCP permite **una sola vía, acotada y sin credenciales**, que es justo lo que pedía la consigna.

**Cómo se usa:** con el cliente de OpenCode (`mcp.filesystem.*`) o, para apuntar a la raíz del repo, con el cliente stdio incluido (`docs/skills-mcp/tools/mcp-fs.js`), que **sólo imprime el resultado de la herramienta invocada** (descarta las respuestas de `initialize` y de `tools/list`). El `INIT` del server y la lista de las 14 herramientas los imprime `docs/skills-mcp/tools/mcp-handshake.js`:

```bash
node docs/skills-mcp/tools/mcp-handshake.js "<raiz>"   # INIT + las 14 tools
```

**Límites:** sólo lectura sobre el proyecto; sin escritura en archivos sensibles; sin datos reales de pacientes; sin credenciales en el repositorio.

**Evidencia de uso:** `opencode mcp list` → 3 servidores conectados; handshake JSON-RPC → `INIT secure-filesystem-server 2.0.0`, 14 tools, `READ CHANGES.md -> 34908 chars`; lectura de §03 y §04 de la KB para construir el spec de C-02.

---

## 4. El change preparado (`C-02 tenancy-core-models`)

**Por qué C-02 y no C-01** (el cambio elegido en la ficha inicial): C-01 quedó **implementado, verificado y archivado** durante esta TP, y el punto 7 exige dejar un change *preparado para implementar*, no implementado ni archivado. C-02 es el siguiente del roadmap (GATE 1, desbloqueado, camino crítico) y se prepara sin depender de funcionalidades inexistentes.

**Qué contiene:**

| Artefacto | Contenido |
|---|---|
| `discovery/explore-c02-tenancy-core-models.md` | 4 ejes × 2 opciones, alternativas descartadas con su razonamiento, deudas diferidas con owner |
| `proposal.md` | Por qué, qué cambia, capabilities, impacto |
| `design.md` | 13 decisiones con rationale y alternativa descartada, riesgos, plan de migración, preguntas abiertas |
| `specs/tenancy/identidad/spec.md` | 5 requirements, **13 escenarios** etiquetados por tipo |
| `tasks.md` | 46 tareas en 8 grupos; **los 13 escenarios referenciados** con su verificación |

**Decisiones tomadas con la skill** (A/A/A/A): `002` altera y no reconstruye · `roles` como `ARRAY` de enum (sin tabla puente, según KB §04) · **repositorios tenant-scoped** (el filtro lo aplica el `UnitOfWork`: R1 por construcción) · seed por comando explícito e idempotente.

**Escenarios del spec:** 4 de funcionamiento esperado · 2 de error de negocio · 7 de borde. Cada uno con su tarea y su comando de comprobación.

---

## 5. La revisión crítica: 8 defectos

| # | Defecto | Gravedad | Cómo se detectó | Corrección |
|---|---|---|---|---|
| D1 | El MCP declaraba "OPERATIVO" **sin estar conectado** | alta | `opencode mcp list` showed 2 servidores, no 3 | entry al config **activo** + `node` con entry absoluto (el shim `npx` parte paths con espacios) |
| D2 | El secreto temporal de `dev` se generaba **sin el aviso** que exige el spec | media | cruce de los 18 escenarios del spec contra sus tests | `logger.warning` + test de regresión verificado en rojo y en verde |
| D3 | `design.md` decía "Secrets: ninguno" de forma inexacta | baja | contraste con la task que exige Postgres real | redacción precisa: credenciales de los service containers, sin secrets de GitHub |
| D4 | Caracteres CJK en 4 archivos escritos por el agente | baja | barrido `[\u4e00-\u9fff]` | corregidos; commit verificado limpio |
| D5 | El agente introdujo 2 CVE moderados (`react-router-dom` 6.x) | media | `npm audit` | 7.18.4 + vitest 5.0.5 → audit en 0 |
| D6 | El spec de C-02 **contradecía** el contrato de error de `foundation/runtime` | alta | cruce contra el spec archivado; verificado que ningún RN cubre el caso | `409 {code, message}` con código genérico + escenario 3.3 nuevo |
| D7 | La migración `002` dejaba `slug` nullable y rompía el seed archivado | alta | **experimento en Postgres 16** (índice único admite N NULL) + cruce con `seed_demo.py` | `SET NOT NULL` + backfill con colisión explícita + upstream del seed (Decisión 13) |
| D8 | El spec filtraba un detalle de implementación | baja | relectura contra las reglas de redacción de specs | reescrito en términos observables; la aserción pasó a las tareas |

**Prueba de borde sobre los límites del validador:** con D6 presente, `openspec validate --strict` decía *"is valid"*. El validador comprueba la **forma** de cada delta, pero no cruza specs, ni confronta el plan de migración con la semántica del motor, ni revisa el código existente. Por eso la verificación cruzada quedó escrita como **tarea 8.6** del change y no como confianza en la herramienta.

---

## 6. Problemas de acceso y compatibilidad que hubo que resolver

Registro exigido por la consideración *"Criterio profesional"*.

1. **El servidor MCP no arrancaba** (`Error: None of the specified directories are accessible`): el shim `npx.cmd` de Windows parte el argumento cuando el path tiene espacios. Solución: invocar `node` con el entry absoluto del paquete.
2. **La entry estaba en el archivo de config equivocado**: `opencode.jsonc` no lo lee el cliente; el activo es `opencode.json`. Solución: entry en el archivo correcto, documentada con backups.
3. **Engram no resolvía el proyecto** porque el repositorio está anidado dentro de otro con el mismo remoto Git. Solución: `.engram/config.json` en el repo + `ENGRAM_PROJECT` en la config del cliente.
4. **La suite pasaba en SQLite con datos inválidos**: al correr contra Postgres 16 aparecieron **3 violaciones de FK reales** que SQLite no detecta. Solución: fixtures con el orden de insert correcto y la suite migrada a Postgres real.
5. **El agente se auto-contaminó con caracteres CJK** al escribir: barrido y corrección.
6. **`pydantic-settings` lee `os.environ` incluso en `model_validate`**: para aislar un entorno de test hay que sobreescribir `settings_customise_sources`.
7. **`pytest.ini` con `addopts=-q` + un `-q` extra produce `-qq`** y pytest 9 omite el resumen de resultados: el `-q` de la línea de comandos duplica el del `ini`.

---

## 7. Cómo reproducir

```bash
# 1. Base de datos de test
docker run -d --name odontologia-test-pg -e POSTGRES_USER=odontologia \
  -e POSTGRES_PASSWORD=odontologia -e POSTGRES_DB=odontologia_test -p 55432:5432 postgres:16

# 2. Skill (ya está en el repo; para instalarla globalmente)
cp .opencode/skills/visual-explore-options/SKILL.md ~/.config/opencode/skills/visual-explore-options/

# 3. MCP
npm install -g @modelcontextprotocol/server-filesystem
# entry en ~/.config/opencode/opencode.json -> ver mcp-configuracion.md

# Comprobar la conexión:
opencode mcp list

# Ver INIT y la lista de herramientas del server (lo que mcp-fs.js no imprime):
node docs/skills-mcp/tools/mcp-handshake.js "<raiz>"

# Ejecutar una herramienta real (mcp-fs.js imprime sólo su resultado):
node docs/skills-mcp/tools/mcp-fs.js "<raiz>" read_text_file

# 4. Memoria del proyecto
engram projects list
engram search "C-01" --project odontologia-tpmetodologia

# 5. Tests
cd backend && pip install -r requirements.txt && python -m pytest        # 75 passed
cd frontend && npm install && npm test && npm run typecheck && npm run build   # 10 passed

# 6. Flujo SDD
openspec list --specs
openspec validate --all --strict
openspec status --change C-02-tenancy-core-models
```

---

## 8. Limitaciones y pendientes

- **El video de 5 minutos no se graba** (decisión del equipo): el repositorio incluye la evidencia en texto de las invocaciones reales, que es lo que el punto 8 pide acreditar.
- **El `.zip` final** lo genera el script `docs/skills-mcp/tools/entrega.ps1` con los apellidos `Herrera-Zalazar`; `ENTREGA.md` tiene el commit de entrega y los integrantes.
- **La skill se validó con 6 pruebas de `skill-creator`**, no con usuarios reales de la clínica.
- **El change C-02 está preparado, no implementado**: sus 46 tareas y la verificación de los 13 escenarios quedan pendientes para la instancia siguiente.
- **La instancia del MCP que abre el cliente de OpenCode** queda rooteada en el workspace de la sesión; para consultar el repo con la raíz correcta está el cliente stdio incluido.

---

## 9. Mapa de archivos

```
ENTREGA.md                    Entrega: integrantes, enlaces, reproducción, empaquetado
.atl/skill-registry.md        Registro de skills (nombre, propósito, ubicación, uso)
AGENTS.md                     Instrucciones del agente: skills + integración MCP
docs/skills-mcp/
├── investigacion.md           Ficha puntos 1-4 (2 págs.) + PDF
├── aplicacion.md             Informe puntos 5-6 (2 págs.) + PDF
├── preparacion.md            Punto 7: change preparado + PDF
├── revision-critica.md       Punto 8: revisión crítica + PDF
├── revision-critica-punto-8.md / -c02.md   Evidencia detallada
├── mcp-configuracion.md      Requisitos, instalación, comprobación, solución de problemas
├── evidencias/               Registros reales: MCP, tests, openspec, experimento, defectos
└── tools/                    mcp-fs.js (cliente MCP), md2pdf.py (PDFs), entrega.ps1 (zip)
openspec/changes/C-02-tenancy-core-models/   Artefactos SDD del change preparado
discovery/explore-c02-tenancy-core-models.md  Artefacto del explore con la skill
.engram/config.json           Ata la memoria del proyecto al repositorio
```
