---
name: visual-explore-options
description: Estandariza la fase explore de Spec-Driven Development presentando al menos 2 opciones tecnicas con por-que, como se usa y esquema ASCII, y pausando por seleccion antes de design.md. Usa esta skill siempre que inicies la exploracion de un change que implique decisiones de arquitectura, frontend, backend, base de datos, APIs o componentes, incluso si el usuario no pide explicitamente comparar opciones.
---

# Visual Explore Options

Estandariza la etapa `explore` de SDD. No avances a `design.md` sin seleccion explicita del usuario.

## Cuando activar

Activa cuando:
- Inicias `explore` de un change nuevo con decisiones abiertas, o
- El contexto menciona arquitectura, componentes UI, backend, schema DB, API, o trade-offs tecnicos.

Si el change es trivial (bug de una linea, rename, sin alternativas), explica en 2 lineas por que no hay opciones y pide confirmacion para seguir.

## Entradas

1. Lee el contexto del change: `proposal.md`, `openspec/proposal.md`, `CHANGES.md`, o roadmap del repo. Si no existe, pide: objetivo, restricciones y stack actual.
2. Identifica restricciones duras: stack existente, DB existente, performance, equipo.

## Procedimiento

Sigue estos pasos en orden. Usa forma imperativa y lenguaje simple, sin jerga innecesaria.

### 1. Identifica al menos 2 alternativas viables

Evalua al menos 2 opciones reales. No inventes opciones de relleno. Para cada una indica:
- Que es (1-2 lineas, simple)
- Por que y como se usaria en este proyecto (tecnologia + uso concreto: hooks, validacion, ORM, migraciones, etc.)
- Trade-offs: ventaja principal + costo/riesgo principal

### 2. Genera esquema visual o conceptual ASCII

- Frontend/UI: layout en bloque ASCII dentro de ```text.
- Backend/DB/Arquitectura: flujo en una linea o capas:
  `[ Cliente ] ---> ( Servidor / Rutas ) ---> [ Base de Datos ]`
- Mantenlo pequeno: max 10 lineas, solo cajas y flechas, sin arte complejo.

### 3. Presenta con esta plantilla exacta

Usa SIEMPRE esta plantilla:

```markdown
## Opcion A: [Nombre corto]
* **Que es?:** [1-2 lineas simples]
* **Por que y como:** [tecnologia + por que elegida + como se usa en este change]
* **Trade-off:** Pro: [uno] / Contra: [uno]
* **Esquema:**
```text
[ASCII aqui]
```

## Opcion B: [Nombre corto]
(mismo formato)

## Recomendacion
[1-3 lineas: cual conviene y por que, sin imponer]

[PAUSA OBLIGATORIA]
Indica que opcion deseas (A, B, o combinacion) para generar `design.md`.
```

### 4. Pausa obligatoria

Termina SIEMPRE con la pausa. No generes `design.md`, no escribas codigo, no asumas eleccion. Espera respuesta explicita.

## Criterios de calidad

- Cada opcion justifica por-que y como en lenguaje simple.
- Esquemas en bloque ```text, limpios y cortos.
- Al menos 2 opciones comparables, no una obvia + una absurda.
- Flujo detenido hasta seleccion.

## Ejemplo backend (resumido)

## Opcion A: REST con FastAPI + PostgreSQL
* **Que es?:** Peticiones por rutas ordenadas hacia un servidor que guarda en DB relacional.
* **Por que y como:** FastAPI por validacion automatica y docs interactivas para rutas de turnos. SQLAlchemy como ORM contra PostgreSQL para mantener queries limpias + migraciones con Alembic.
* **Trade-off:** Pro: tipado y rapidez / Contra: requiere modelar schema upfront
* **Esquema:**
```text
[ Cliente HTTP ] ---> ( FastAPI / Rutas ) ---> [ PostgreSQL ]
```
