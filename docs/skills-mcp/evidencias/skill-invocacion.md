# Evidencia de la invocación de la skill `visual-explore-options`

## 1. Solicitud realizada

Herramienta `skill` de OpenCode, dos veces, una por cada preparación:

```
skill({ id: "visual-explore-options" })
```

- **Primera preparación (C-01):** exploración del change inicial. 4 ejes × 2 opciones; el usuario eligió A/A/A/A + Postgres 16 real.
- **Segunda preparación (C-02, este TP):** exploración del change preparado. 4 ejes × 2 opciones; el usuario eligió "aplica las opciones que recomendaste".

## 2. Resultado obtenido

El `SKILL.md` completo, con su procedimiento (restricciones duras → ≥2 alternativas comparables → explicitación práctica → esquema ASCII → plantilla exacta → recomendación → **pausa obligatoria**) y sus criterios de revisión.

Los artefactos que produjo:

| Preparación | Artefacto | Contenido |
|---|---|---|
| C-01 | `discovery/explore-c01-foundation-setup-decisiones.md` | 4 ejes × 2 opciones, esquemas ASCII, recomendación y la pausa final |
| C-02 | `discovery/explore-c02-tenancy-core-models.md` | 4 ejes × 2 opciones, alternativas descartadas con su razonamiento, §8 de deudas diferidas con owner y la tabla de decisiones tomadas (§0) |

**La pausa obligatoria se respetó en las dos:** no se generó `proposal.md` ni `design.md` hasta que el usuario respondió. En C-02 la secuencia fue: explore → opciones presentadas → **"aplica las opciones que recomendaste"** → `proposal.md` + `design.md` + `spec.md` + `tasks.md`.

## 3. Qué aportó al change

1. **Forzó la comparación explícita antes de fijar el esquema.** En C-02, el eje decisivo fue *repositorio tenant-scoped* frente a *`tenant_id` explícito en cada llamada*: la skill obligó a poner la alternativa sobre la mesa, y de ahí salió que R1 (la regla dura #1) pasara de depender de la disciplina a depender de la estructura.
2. **Detectó la colisión de migraciones** entre `0001_cancelacion_turno` (ya existente) y la `002` que el plan asignaba a C-02, y dejó por escrito que `0001` no se toca.
3. **Puso en pausa la escritura de código** justo donde hacía falta, en las dos preparaciones.
4. **Dejó el porqué de cada alternativa descartada**, que es lo que permite cuestionarla después. Ejemplo: la tabla puente de roles quedó descartada **porque contradice la KB §04**, y por eso el `design.md` cita la KB en lugar de una preferencia.
5. **En el punto 8 fue el insumo de la evidencia**: la comparación de alternativas es la que permitió distinguir un error de diseño (D6: el spec de C-02 contradecía el contrato de error de `foundation/runtime`) de una decisión discutible.

## 4. Comprobación en sesión nueva

La skill se localizó y se cargó por las referencias del proyecto, sin ayuda externa:

- `AGENTS.md` §Skills disponibles la lista con propósito, condiciones de activación y cómo revisar el resultado.
- `.atl/skill-registry.md` la registra con nombre, propósito, ubicación y situaciones de uso.
- Copias en `.opencode/skills/`, `.claude/skills/`, `.devin/skills/` y `skills/`.

Además, `skill-creator` generó **6 pruebas** (3 con skill + 3 baseline) para contrastar el resultado de la skill con y sin ella: **con skill 15/15 (100 %) vs. baseline 6/15 (40 %)** en aserciones de plantilla, esquema ASCII, pausa obligatoria y recomendación.
