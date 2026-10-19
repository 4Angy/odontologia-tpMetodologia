# ADR-003 — Contrato de migrabilidad v1 → v2 hacia odontograma FDI

- **Estado:** aceptada
- **Fecha:** 2026-10-19
- **Decide:** C-01 `foundation-setup-decisiones`
- **Cierra (parcialmente):** R1 — "salir en v1 sin odontograma cuando los 15 competidores lo tienen como núcleo"
- **Owner del comportamiento:** **C-05** (`ficha-clinica-presupuestos`)
- **Contexto de riesgo:** DD-01, `knowledge-base/09_decisiones_y_supuestos.md`

## 1. Contexto

DD-01 decidió que v1 sale con agenda + recordatorios + caja/señas + ficha mínima, y que el odontograma (y la HCE completa) van a v2+. El riesgo **R1** es explícito: *los 15 competidores tienen odontograma como núcleo, y salir sin él va contra el estándar de mercado*.

C-01 tiene que dejar el plan de migración "por escrito" (scope de CHANGES.md). Un plan en prosa no es una garantía: es una promesa que nadie verifica. Lo que hace falta es un **contrato de campos** que C-05 pueda cumplir y que un test pueda comprobar.

El dato clave: **`evolucion` todavía no existe** (la crea C-05). C-01 no puede migrar datos — no hay datos. Lo que sí puede, y debe, es **fijar la forma** que los datos van a tener, de modo que la migración a FDI no tenga que adivinar nada.

## 2. Contrato de campos y regla de proyección

### 2.1 Campos de `evolucion` v1

| Campo | Tipo | Papel en la proyección a FDI v2 | ¿Migrable? |
|---|---|---|---|
| `id` | id | se conserva | sí |
| `tenant_id` | FK | se conserva | sí |
| `paciente_id` | FK | se conserva | sí |
| `profesional_id` | FK | se conserva | sí |
| `fecha` | timestamptz UTC | se conserva (R7) | sí |
| `motivo` | texto | texto libre de la pieza | sí |
| `detalle` | texto | texto libre de la pieza | sí |
| **`pieza_fdi_slot`** | enum nullable: `dent` \| `face` \| `tooth` \| `zone` | **ancla de la pieza** (notación FDI) | sí — es el ancla |
| **`pieza_fdi_numero`** | int nullable | **número FDI** de la pieza (1-32 adulto / A-E deciduo) | sí — es el ancla |
| `odontograma_ref` | id nullable | referencia al registro FDI v2 | sí (FK lógica) |
| `firma_simple` | bool | alcance legal declarado | sí |
| `firmado_at` | timestamptz UTC nullable | marca temporal de la firma | sí |

**Invariante del ancla:** `pieza_fdi_slot` y `pieza_fdi_numero` van juntos o no van. Si `pieza_fdi_slot IS NOT NULL`, entonces `pieza_fdi_numero IS NOT NULL` y viceversa. Un campo sin el otro no se puede proyectar.

### 2.2 Regla de proyección

Para cada `evolucion` v1, la proyección a un registro de odontograma FDI v2 es:

1. Si `(pieza_fdi_slot, pieza_fdi_numero)` no es NULL → se crea el registro FDI con esa pieza, y la `evolucion` queda **anclada** a ese registro (`odontograma_ref`).
2. Si la ancla es NULL → la `evolucion` queda como **evolución sin pieza** (texto libre). En v2 esto es un registro FDI "sin pieza" o una nota clínica, según el modelo que se elija; en ningún caso se **descarta** ni se **adivina** una pieza.
3. `motivo`, `detalle`, `fecha`, `firma_simple` y `firmado_at` viajan íntegros en ambos casos.
4. La proyección es **determinista y reversible**: dado un `evolucion` v1, el resultado FDI está determinado por el contrato; y dado el FDI, se puede volver al `evolucion` v1 sin pérdida.

### 2.3 Lo que NO se decide aquí

- El modelo de datos del odontograma FDI v2 (piezas, caras, zonas, periodontograma). Es de v2.
- Si `evolucion` con ancla nula se migra a una "pieza genérica" o a una nota clínica. Es de v2.
- La versión del esquema FDI que se usa. Es de v2.

## 3. Criterio de aceptación que hereda C-05

C-05 agrega a sus criterios de aceptación, y a su suite de tests:

> **Requisito (migrabilidad):** toda `evolucion` creada bajo el contrato v1 es proyectable a odontograma FDI v2 **sin pérdida de información relevante**.

Verificación:

1. **Test de proyección:** dada una `evolucion` con ancla FDI, la proyección produce un registro FDI con la misma pieza, y el `motivo`, `detalle`, `fecha`, `firma_simple` y `firmado_at` se conservan.
2. **Test de evolución sin pieza:** dada una `evolucion` sin ancla, la proyección no inventa una pieza y no descarta el texto.
3. **Test del ancla:** `pieza_fdi_slot` y `pieza_fdi_numero` no pueden quedar uno sin el otro (constraint de base de datos o validación de dominio).
4. **Test de idempotencia:** proyectar dos veces la misma `evolucion` no duplica el registro FDI.

## Alternativas descartadas

- **Nota narrativa ("en v2 se migra a FDI"):** cero costo en C-01, pero deja la deuda abierta y la descubrible tarde, cuando el odontograma v2 ya tenga datos de v1 que no encajan. Eso es R1 sin mitigating.
- **Tabla `evolucion` genérica sin campos FDI** (sólo texto libre) y que la migración a FDI se resuelva en v2: imposible de automatizar sin intervención manual sobre cada registro. Descartado.
- **Adelantar el odontograma FDI a v1:** contradice DD-01 y el análisis competitivo (§D.3) que lo deja para v2+ con el gatillo de las demos. Descartado para este change.

## Consecuencias

- **C-05** diseña `evolucion` cumpliendo el contrato de la sección 2.1 y agrega el criterio de aceptación de la sección 3.
- **C-13** revisa si el gatillo de §D.3 (que el odontograma sea eliminatorio en las demos) se activó: si se activa, el odontograma entra en v1 y este contrato se convierte en la base de la migración inversa (FDI → `evolucion`).
- **Riesgo residual:** el contrato garantiza que la migración **técnica** es posible, no que el odontograma v2 sea igual de útil que el de los competidores. R1 no desaparece: se acota y se hace explícito.
