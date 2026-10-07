# Consultorio Odontológico SaaS — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnologías | Versión mínima |
|------|-------------|----------------|
| Backend | Python + FastAPI + SQLAlchemy | Python 3.12, FastAPI 0.110+ |
| Auth | JWT (access + refresh) | — |
| Base de datos | PostgreSQL | 16 |
| Cache / colas / jobs | Redis (cache + cola de jobs + scheduler) | 7 |
| Frontend | React + TypeScript + Vite | React 18, TS 5 |
| Contenedores | Docker + Docker Compose (dev y deploy inicial) | Docker 24 |
| Mensajería v1 | WhatsApp (proveedor por decidir — PA-01) | — |
| Cobros v1 | Mercado Pago SDK (solo seña) | API vigente 2026 |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |

> ⚠️ Resolver las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` (PA-01 WhatsApp, PA-02 facturación, PA-03 Dental Manager/MednIA) antes de arrancar el primer change.

---

## Skills Disponibles

Fuente de verdad: `.atl/skill-registry.md` (16 skills indexadas; sin skills de dominio instaladas — rigen KB + CHANGES).

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / tenancy / RBAC / agenda / caja | Registry + KB (sin skill de dominio: aplicar reglas duras R1–R9) |
| **Frontend** | React / agenda día-semana / ficha / reserva pública | `impeccable` (pulido UI), registry + KB |
| **Integraciones** | WhatsApp worker / MP webhooks | `web-scraper` (docs oficiales), registry + KB |
| **Orquestación** | OPSX / SDD / docs | `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`, `kb-creator`, `roadmap-generator` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 13 changes en 6 fases (GATE 0–8, plan de 3 agentes).
- **Camino crítico** (9): `C-01 → C-02 → C-03 → C-04 → C-07 → C-08 → C-09 → C-10 → C-13`.
- **Rama co-crítica comercial**: `C-11 → C-12` (caja + seña MP, diferenciador DD-05).
- **Primer change**: `C-01` (foundation-setup-decisiones: scaffolding + ADR-001 WhatsApp + ADR-002 facturación + plan migración R1→odontograma).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> No hay `~/.claude/CLAUDE.md` global en este entorno: este archivo es autocontenido. Incluye universales + específicas del proyecto. Son contrato; romperlas es un defecto. Confirmadas con el usuario.

**Multi-tenancy (riesgo #1 de la arquitectura):**
- R1. NUNCA una query de negocio sin `tenant_id` del JWT → dato cruzado entre consultorios es defecto crítico.
- R2. NUNCA confiar el tenant desde el frontend → siempre del JWT validado en backend.

**Backend (FastAPI / SQLAlchemy):**
- R3. NUNCA exponer modelos SQLAlchemy en la API → DTOs Pydantic v2.
- R4. NUNCA schema Pydantic sin `extra='forbid'` → rechazar campos no declarados.
- R5. NUNCA montos de dinero en `float` → centavos enteros en todos lados.
- R6. NUNCA migración Alembic sin `downgrade` → reversible siempre.
- R7. NUNCA datetime naive → todo UTC con timezone.

**Dinero + webhooks:**
- R8. NUNCA procesar un webhook (MP/WhatsApp) sin clave de idempotencia → `mp_payment_id` / `provider_msg_id`.
- R9. NUNCA un error de negocio sin `code` trazable a RN-XX (ej. cancelación <24h → `RN-AG-01`).

**Frontend (React + TS):**
- R10. NUNCA `any` explícito → TypeScript estricto; componentes en PascalCase.

**Datos sensibles:**
- R14. NUNCA almacenar datos reales sensibles de pacientes → dev/tests/seeds solo con datos sintéticos/demo.

**Universales:**
- R11. TDD estricto: test en rojo antes del código, mínimo 2 casos por comportamiento.
- R12. NUNCA commit/push sin pedido explícito → conventional commits cuando se pida.
- R13. Datos de salud + cobros = gobernanza CRITICAL/HIGH → análisis y propuesta antes de escribir código, sin atajos.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
