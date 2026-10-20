# ADR-002 — Alcance de "facturación" en v1: caja manual, sin comprobante

- **Estado:** aceptada
- **Fecha:** 2026-10-19
- **Decide:** C-01 `foundation-setup-decisiones`
- **Cierra:** PA-02 e IN-01 (`knowledge-base/10_preguntas_abiertas.md`)
- **Owner del comportamiento:** **C-11** (`cobros-caja-manual`)
- **Revisión:** si en las demos de §D.1 del análisis competitivo la objeción "necesito un comprobante" aparece de forma repetida, el recibo interno numerado entra como change de **v2** con su propio ADR.

## 1. Contexto

RN-CO-01 y DD-02 ya decidían que "facturación" en v1 significa caja manual, sin comprobantes fiscales ni integración con AFIP/ARCA. Lo que faltaba era **operacionalizarlo** para C-11, que hoy no sabe si su modelo `cobros/` debe incluir un comprobante.

Dos cosas presionan en direcciones opuestas:

- **SU-03 (supuesto sin probar):** el dueño acepta "caja, no factura" si se declara honestamente. Si no, hay churn temprano por expectativa fiscal.
- **El mercado sí factura:** DrApp y Benty publican facturación ARCA; Dentatools declara explícitamente que **no** hace factura AFIP, y el análisis competitivo lo señala como un diferenciador de *transparencia negativa* (§C.2).

## 2. Decisión

**"Facturación" v1 = caja manual, sin ningún comprobante.**

El módulo `cobros/` queda en **exactamente dos tablas**:

| Tabla | Contenido | Reglas |
|---|---|---|
| `cobro` | `id`, `tenant_id`, `paciente_id`, `turno_id` nullable, `monto_centavos` (entero), `medio` (`efectivo` \| `transferencia` \| `mp` \| `otro`), `concepto`, `cobrado_por` (usuario), `fecha` (timestamptz UTC) | Todos los montos en **centavos enteros** (R5). |
| `cierre_caja` | `tenant_id`, `fecha`, totales por medio, `observaciones`, `cerrado_por`, `cerrado_at` | **Inmutable** una vez cerrado: sólo nota de ajuste auditada, nunca edición (RN-CO-04). |

Y **tres ausencias explícitas**, que C-11 no debe crear:

- **No** existe la tabla `recibo`.
- **No** existe el campo `cobro.numero_comprobante`.
- **No** existe numeración correlativa de ningún tipo en v1.

Reglas que se mantienen sin cambios:

- **RN-CO-05:** el saldo y la deuda del paciente son **siempre derivados** (`cobros − presupuestos − señas aplicadas`). Ningún endpoint los edita directamente. `saldo` no es una columna.
- **RN-CO-04:** el cierre diario es inmutable; los ajustes son notas auditadas (RN-GL-02), nunca edición de un cierre.
- **RN-CO-02 / RN-CO-03:** la seña por Mercado Pago y su política de devolución son de C-12, no de este ADR. La seña **no** es un `cobro`: son dos cosas distintas.

**Lo que esto NO es:** un comprobante fiscal. El sistema no emite facturas, no se integra con ARCA/AFIP y no genera numeraciones con validez legal. Integrar ARCA en v1 multiplicaría costo y riesgo (DD-02), y la facturación electrónica queda explícitamente fuera de v1 (`02_descripcion_general.md` §Integraciones externas).

## 3. Declaración de UI (obligatoria)

RN-CO-01 lo exige: *"la UI lo declara para no defraudar expectativas"*. C-11 y C-13 deben mostrar, en la pantalla de caja, un aviso permanente con esta redacción:

> **Caja manual, sin comprobantes fiscales.** Esta versión registra cobros, saldos, deudas y el cierre del día, pero **no emite facturas ni comprobantes electrónicos**. Si tu consultorio necesita facturación electrónica (ARCA), todavía no está disponible.

La declaración va, como mínimo, en: (a) la pantalla de caja, (b) la pantalla de deudas, (c) el cierre del día, (d) la landing y el onboarding (C-13). No es un texto de "términos" al que haya que llegar leyendo: es visible en el punto donde el dueño mira los números.

## 4. Criterio de re-evaluación (recibo interno)

Si el dueño insiste en "un papel", el paso siguiente **no** es ARCA sino un **recibo interno numerado, no fiscal**: un PDF con numeración correlativa por tenant, leyenda explícita de "sin valor fiscal" y descarga desde la pantalla de cobro.

Condiciones para abrirlo:

1. La objeción aparece de forma **repetida** en demos o entrevistas (no una vez).
2. Entra como **change de v2 con su propio ADR**, no como parche de C-01 ni de C-11.
3. C-11 (que ya es CRITICO por dinero) no crece en alcance dentro de v1.

Lo que ese change de v2 tendría que resolver, y que aquí **no** se decide: numeración correlativa por tenant con control de concurrencia, plantilla del PDF, leyenda anti-confusión, y si el recibo se puede reimprimir (y qué queda registrado al reimprimir).

## Alternativas descartadas

- **Recibo interno numerado (no fiscal) en v1:** es la alternativa (b) de DD-02. Se descarta para v1 porque suma alcance a un change CRITICO (C-11) y abre la peor confusión posible: el dueño leería "recibo" como "factura" y la decepción sería peor que con caja pura. Queda como v2 (sección 4).
- **Facturación electrónica ARCA en v1:** multiplica costo y riesgo, requiere certificación y proveedor, y contradice el filtro de costo operativo bajo. Fuera de v1 por decisión de la KB.

## Consecuencias

- **C-11** implementa `cobro` + `cierre_caja` con saldo derivado e inmutabilidad del cierre, y muestra la declaración de la sección 3.
- **C-12** (seña MP) mantiene la seña **fuera** de `cobro`: son entidades distintas con reglas distintas.
- **C-13** publica la declaración en landing y onboarding y mide la objeción fiscal en las demos.
- **Riesgo residual:** SU-03 (que caja manual no defrauda) sigue sin probarse. Está mitigado con la declaración explícita y la medición de objeciones, no con código.
