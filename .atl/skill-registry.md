# Registro de Skills del Proyecto

Registro de las skills disponibles para el agente. Formato: **nombre · propósito · ubicación · situaciones de uso**.

> Este archivo lo mantiene el equipo del proyecto. Si el orquestador lo regenera, verificar que la entry de `visual-explore-options` siga presente (es la que sostiene el punto 5 del TP).

| Skill | Propósito | Ubicación | Situaciones de uso |
|---|---|---|---|
| `visual-explore-options` | Estandarizar la fase `explore` del flujo Spec-Driven Development: presentar **al menos 2 alternativas técnicas comparables** (qué es / por qué y cómo / trade-off / esquema ASCII) con una plantilla exacta y una **pausa obligatoria** antes de generar `design.md`. | `.opencode/skills/visual-explore-options/SKILL.md` (en el repo) · réplicas en `.claude/skills/`, `.devin/skills/`, `skills/visual-explore-options.md` · instalación global en `~/.config/opencode/skills/` | Al iniciar el `explore` de un change con decisiones abiertas, o cuando el contexto menciona arquitectura, UI, backend, schema de base de datos, APIs o trade-offs técnicos. |
| `skill-creator` | Crear y evaluar skills nuevas (genera el `SKILL.md`, aplica el frontmatter y produce pruebas de comparación con/sin skill). | Global: `~/.config/opencode/skills/skill-creator/` | Al crear una skill propia o al evaluar una skill generada con IA. |
| `web-scraper` | Extraer de una URL: problema que resuelve, usuarios, features, pricing y posicionamiento, en notas markdown con esquema fijo. | Global: `~/.config/opencode/skills/web-scraper/` | En la fase de discovery, al investigar competidores o proveedores de un stack. |
| `session-checkpoint` | Guardar el estado de una sesión (archivos, pendientes, prompt de arranque) ante agotamiento de tokens o cierre. | Global: `~/.config/opencode/skills/session-checkpoint/` | Antes de un cierre de sesión o de una compactación. |
| `find-skill` | Buscar e instalar skills existentes para una capacidad concreta. | Global: `~/.config/opencode/skills/find-skill/` | Cuando una tarea repetitiva necesita una skill que todavía no existe en el proyecto. |

## Notas

- **Instalación fuera del repositorio:** `visual-explore-options` también está en `~/.config/opencode/skills/`, pero la **copia versionada** del repo es la fuente de verdad; las instrucciones reproducibles están en `AGENTS.md` §Skills disponibles y en `docs/skills-mcp/mcp-configuracion.md` §2 (patrón equivalente para el MCP).
- **Cómo se comprueba que el agente la encuentra:** `AGENTS.md` §Skills disponibles la lista con su propósito y sus condiciones de activación, y `docs/skills-mcp/aplicacion.md` §1 registra la evidencia de uso (artefacto del explore de C-02 y las 6 pruebas con/sin skill de `skill-creator`).
