# ADRs — Registro de decisiones de arquitectura

Decisiones de arquitectura del proyecto, con su contexto, su justificación, las alternativas descartadas y el *change* que es dueño de implementarlas.

Un ADR **no** es un contrato de comportamiento: los contratos de comportamiento viven en los specs de OpenSpec (`openspec/specs/`) y en la KB (`knowledge-base/`). Un ADR registra **por qué** se eligió una camino y **cuándo** se puede revisar.

## Índice

| ADR | Título | Estado | Cierra | Owner del comportamiento | Fecha |
|---|---|---|---|---|---|
| [ADR-001](ADR-001-whatsapp-provider.md) | Proveedor de WhatsApp en v1: `official` (Cloud API de Meta) | aceptada | PA-01 | C-09 | 2026-10-19 |
| [ADR-002](ADR-002-alcance-facturacion.md) | Alcance de "facturación" en v1: caja manual, sin comprobante | aceptada | PA-02, IN-01 | C-11 | 2026-10-19 |
| [ADR-003](ADR-003-migrabilidad-fdi.md) | Contrato de migrabilidad v1 → v2 hacia odontograma FDI | aceptada | R1 (parcialmente) | C-05 | 2026-10-19 |

## Contexto

- `knowledge-base/09_decisiones_y_supuestos.md` — decisiones de producto (DD-xx) y supuestos (SU-xx).
- `knowledge-base/10_preguntas_abiertas.md` — preguntas abiertas (PA-xx) e inconsistencias (IN-xx). Los ADR cierran PA-xx.
- `discovery/analisis-competitivo.md` — evidencia de mercado que sustenta las decisiones.

## Reglas

1. Un ADR se escribe **antes** de implementar el comportamiento que decide.
2. Un ADR tiene **owner**: el change que lo implementa y que lo puede revertir.
3. Un ADR **no se borra**: si una decisión cambia, se escribe uno nuevo que lo referencie.
4. Toda decisión de C-01 sale de `discovery/explore-c01-foundation-setup-decisiones.md`.
